from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Tournament
from services.sendgrid_service import send_email
import json
import logging

# Initialize blueprint
user_bp = Blueprint('user', __name__)

@user_bp.route('/home')
@login_required
def home():
    # Get user data
    user = User.query.get(current_user.id)
    
    # Get attending tournaments with specific days/sessions selected
    attending_ids = []
    if user.attending:
        for tournament_id, attendance_data in user.attending.items():
            attending_ids.append(tournament_id)
    
    # Get future tournaments (after today's date)
    from datetime import datetime
    today = datetime.now().date()
    
    # Get all attending tournaments
    all_attending = Tournament.query.filter(Tournament.id.in_(attending_ids)).all() if attending_ids else []
    
    # Get all the user's past tournaments (from past_tournaments field)
    past_tournament_ids = user.past_tournaments if user.past_tournaments else []
    past_tournaments_attended = Tournament.query.filter(Tournament.id.in_(past_tournament_ids)).all() if past_tournament_ids else []
    
    # Split attending tournaments into past and upcoming
    upcoming_tournaments = [t for t in all_attending if t.end_date >= today]
    
    # Calculate attendance counts for each tournament
    attendance_counts = {}
    for tournament in upcoming_tournaments:
        # Count users attending this tournament
        attending_count = User.query.filter(
            User.attending.contains({tournament.id: {}})
        ).count()
        
        # Count users open to meeting at this tournament
        meeting_count = User.query.filter(
            User.raised_hand.contains({tournament.id: {}})
        ).count()
        
        attendance_counts[tournament.id] = {
            'attending': attending_count,
            'meeting': meeting_count
        }
    
    return render_template('home.html', 
                          user=user, 
                          upcoming_tournaments=upcoming_tournaments,
                          past_tournaments=past_tournaments_attended,
                          attendance_counts=attendance_counts)

# Keep the profile route for backward compatibility, redirecting to home
@user_bp.route('/profile')
@login_required
def profile():
    return redirect(url_for('user.home'))

@user_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    notifications = 'notifications' in request.form
    
    # Update user in database
    user = User.query.get(current_user.id)
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    
    # Also update the name field for backward compatibility
    if first_name and last_name:
        user.name = f"{first_name} {last_name}"
    
    user.notifications = notifications
    db.session.commit()
    
    # Clear temporary password after profile update (if exists)
    if 'temp_password' in session:
        del session['temp_password']
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('user.profile'))

@user_bp.route('/profile/attending', methods=['POST'])
@login_required
def update_attending():
    # Get the tournaments the user wants to attend
    attending_ids = request.form.getlist('attending')
    
    # Update user in database
    user = User.query.get(current_user.id)
    
    # Get the current attending data (dictionary)
    current_attending = dict(user.attending) if user.attending else {}
    
    # Get all previously selected tournaments that are no longer selected
    to_remove = [t_id for t_id in current_attending.keys() if t_id not in attending_ids]
    
    # Remove tournaments no longer selected
    for t_id in to_remove:
        if t_id in current_attending:
            del current_attending[t_id]
    
    # Add newly selected tournaments with empty day/session structure
    for t_id in attending_ids:
        if t_id not in current_attending:
            # Initialize with an empty structure for days/sessions
            current_attending[t_id] = {}
    
    # Update the user's attending information
    user.attending = current_attending
    db.session.commit()
    
    flash('Tournament preferences updated!', 'success')
    return redirect(url_for('user.home'))

@user_bp.route('/settings')
@login_required
def settings():
    # Get user data
    user = User.query.get(current_user.id)
    
    return render_template('settings.html', user=user)

@user_bp.route('/toggle_notifications')
@login_required
def toggle_notifications():
    # Toggle notifications setting
    user = User.query.get(current_user.id)
    user.notifications = not user.notifications
    db.session.commit()
    
    status = "enabled" if user.notifications else "disabled"
    flash(f'Notifications {status}!', 'success')
    return redirect(url_for('user.settings'))

@user_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Check if new password and confirmation match
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('user.settings'))
    
    # Get the current user
    user = User.query.get(current_user.id)
    
    # If a current password was provided, verify it
    if current_password and user.password_hash:
        if not check_password_hash(user.password_hash, current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('user.settings'))
    
    # Update the password hash
    try:
        user.password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        db.session.commit()
        
        # Clear temporary password after successful password change (if exists)
        if 'temp_password' in session:
            del session['temp_password']
        
        flash('Password updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating password: {str(e)}")
        flash('An error occurred while updating your password.', 'danger')
    
    return redirect(url_for('user.settings'))

@user_bp.route('/order_lanyard', methods=['GET', 'POST'])
@login_required
def order_lanyard():
    # Check if user is attending any tournaments with raised_hand
    user = User.query.get(current_user.id)
    
    # If lanyard already ordered, just show the confirmation page
    if user.lanyard_ordered:
        return render_template('order_lanyard.html', lanyard_ordered=True)
    
    # Check if the user has raised their hand for any tournament
    has_selected_sessions = False
    if user.raised_hand and len(user.raised_hand) > 0:
        has_selected_sessions = True
    
    if not has_selected_sessions:
        flash('You must select tournament sessions before ordering your lanyard.', 'warning')
        return redirect(url_for('user.home'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        address1 = request.form.get('address1')
        address2 = request.form.get('address2', '')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip')
        country = request.form.get('country')
        
        # Form validation
        if not all([name, address1, city, zip_code, country]):
            flash('Please fill out all required fields.', 'danger')
            return render_template('order_lanyard.html', lanyard_ordered=False)
        
        # Update user in database to mark lanyard as ordered
        user.lanyard_ordered = True
        db.session.commit()
        
        # Send confirmation email to user
        if user.notifications:
            send_email(
                to_email=user.email,
                subject="Your CourtSide Club Lanyard Order",
                html_content=render_template('email/notification.html', 
                                            name=user.get_full_name(),
                                            message="Your lanyard order has been placed! You'll receive it soon.")
            )
        
        # Send admin notification
        admin_email = current_app.config.get('ADMIN_EMAIL')
        if admin_email:
            send_email(
                to_email=admin_email,
                subject="New Lanyard Order",
                html_content=render_template('email/admin_summary.html',
                                            user_email=user.email,
                                            user_name=user.get_full_name(),
                                            shipping_details=f"{name}, {address1}, {city}, {country}")
            )
        
        # Reload the page with the confirmation message
        return redirect(url_for('user.order_lanyard'))
    
    return render_template('order_lanyard.html', lanyard_ordered=False)
