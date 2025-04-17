from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from models import db, User, Tournament
from services.sendgrid_service import send_email
import json

# Initialize blueprint
user_bp = Blueprint('user', __name__)

@user_bp.route('/profile')
@login_required
def profile():
    # Get all tournaments
    tournaments = Tournament.query.all()
    
    # Get user data
    user = User.query.get(current_user.id)
    
    # Get attending tournaments
    attending_ids = list(user.attending.keys()) if user.attending else []
    attending = Tournament.query.filter(Tournament.id.in_(attending_ids)).all() if attending_ids else []
    
    return render_template('profile.html', 
                          user=user,
                          attending=attending,
                          all_tournaments=tournaments)

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
    return redirect(url_for('user.profile'))

@user_bp.route('/toggle_notifications')
@login_required
def toggle_notifications():
    # Toggle notifications setting
    user = User.query.get(current_user.id)
    user.notifications = not user.notifications
    db.session.commit()
    
    status = "enabled" if user.notifications else "disabled"
    flash(f'Notifications {status}!', 'success')
    return redirect(url_for('user.profile'))

@user_bp.route('/order_lanyard', methods=['GET', 'POST'])
@login_required
def order_lanyard():
    # Check if user is attending any tournaments
    user = User.query.get(current_user.id)
    if not user.attending:
        flash('You need to be attending at least one tournament to order a lanyard.', 'warning')
        return redirect(url_for('user.profile'))
    
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
            return render_template('order_lanyard.html')
        
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
        
        flash('Your lanyard has been ordered!', 'success')
        return redirect(url_for('user.profile'))
    
    return render_template('order_lanyard.html')
