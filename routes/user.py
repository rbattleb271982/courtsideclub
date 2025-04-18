from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Tournament, UserTournament
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
    
    # Get future tournaments (after today's date)
    from datetime import datetime
    today = datetime.now().date()
    
    # Get all attending tournaments using the new UserTournament model
    user_tournaments = UserTournament.query.filter_by(user_id=user.id).all()
    attending_ids = [ut.tournament_id for ut in user_tournaments]
    
    # Also include tournaments from legacy JSON field for backward compatibility during migration
    if user.attending:
        for tournament_id in user.attending.keys():
            if tournament_id not in attending_ids:
                attending_ids.append(tournament_id)
    
    # Get all attending tournaments
    all_attending = Tournament.query.filter(Tournament.id.in_(attending_ids)).all() if attending_ids else []
    
    # Get all the user's past tournaments
    # Combine data from both the relationship and the legacy JSON field
    past_tournaments_from_rel = user.attended_tournaments
    past_tournament_ids_legacy = user.past_tournaments_json if hasattr(user, 'past_tournaments_json') else []
    
    # Combine past tournament IDs
    past_tournament_ids = [t.id for t in past_tournaments_from_rel]
    for t_id in past_tournament_ids_legacy:
        if t_id not in past_tournament_ids:
            past_tournament_ids.append(t_id)
    
    past_tournaments_attended = Tournament.query.filter(Tournament.id.in_(past_tournament_ids)).all() if past_tournament_ids else []
    
    # Get current tournament list (not past)
    current_tournaments = [t for t in all_attending if t.end_date >= today]
    
    # Calculate attendance counts for each tournament using new model
    attendance_counts = {}
    for tournament in current_tournaments:
        # Count users attending this tournament - only count those marked with attending=True
        attending_count = UserTournament.query.filter_by(
            tournament_id=tournament.id,
            attending=True
        ).count()
        
        # Count users open to meeting at this tournament - only those attending and open to meet
        meeting_count = UserTournament.query.filter_by(
            tournament_id=tournament.id,
            attending=True,
            open_to_meet=True
        ).count()
        
        attendance_counts[tournament.id] = {
            'attending': attending_count,
            'meeting': meeting_count
        }
    
    return render_template('home.html', 
                          user=user, 
                          upcoming_tournaments=current_tournaments,
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
    
    # Get current UserTournament registrations
    current_registrations = UserTournament.query.filter_by(user_id=user.id).all()
    current_tournament_ids = [reg.tournament_id for reg in current_registrations]
    
    # Identify tournaments to remove and add
    to_remove = [t_id for t_id in current_tournament_ids if t_id not in attending_ids]
    to_add = [t_id for t_id in attending_ids if t_id not in current_tournament_ids]
    
    # Remove tournaments no longer selected
    for t_id in to_remove:
        # Find the UserTournament record and delete it
        registration = UserTournament.query.filter_by(
            user_id=user.id,
            tournament_id=t_id
        ).first()
        if registration:
            db.session.delete(registration)
    
    # Add newly selected tournaments with default settings
    for t_id in to_add:
        # Create a new UserTournament record
        new_registration = UserTournament(
            user_id=user.id,
            tournament_id=t_id,
            dates=[],
            sessions=[],
            open_to_meet=True  # Default to being open to meeting
        )
        db.session.add(new_registration)
    
    # For backward compatibility during migration, also update JSON fields
    # Get the current attending data (dictionary)
    current_attending = dict(user.attending) if user.attending else {}
    
    # Remove tournaments no longer selected from JSON field
    for t_id in to_remove:
        if t_id in current_attending:
            del current_attending[t_id]
    
    # Add newly selected tournaments to JSON field
    for t_id in to_add:
        if t_id not in current_attending:
            # Initialize with an empty structure for days/sessions
            current_attending[t_id] = {}
    
    # Update the user's JSON attending field for backward compatibility
    user.attending = current_attending
    
    # Commit all changes
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
    # List of U.S. state abbreviations
    STATE_ABBRS = [
        "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI", "IA", "ID", "IL", "IN",
        "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ",
        "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA",
        "WI", "WV", "WY"
    ]
    
    user = User.query.get(current_user.id)
    
    # If lanyard already ordered, just show the confirmation page
    if user.lanyard_ordered:
        return render_template('order_lanyard.html', lanyard_ordered=True, states=sorted(STATE_ABBRS))
    
    # Check if user has selected and saved sessions for any tournament
    valid_attendance = UserTournament.query.filter_by(
        user_id=current_user.id, 
        attending=True
    ).filter(UserTournament.sessions.cast(db.String) != '[]').first()

    if not valid_attendance:
        return render_template('order_lanyard.html', no_sessions=True)
    
    # For backward compatibility, also check the legacy raised_hand JSON field
    legacy_check = False
    if hasattr(user, 'raised_hand') and user.raised_hand and len(user.raised_hand) > 0:
        legacy_check = True
    
    is_attending = existing or legacy_check
    
    if not is_attending:
        flash('You must select tournament sessions and save your preferences before ordering your lanyard.', 'warning')
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
            return render_template('order_lanyard.html', lanyard_ordered=False, states=sorted(STATE_ABBRS))
        
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
    
    return render_template('order_lanyard.html', lanyard_ordered=False, states=sorted(STATE_ABBRS))
