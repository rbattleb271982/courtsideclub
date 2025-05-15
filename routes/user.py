from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Tournament, UserTournament, past_tournaments
from services.sendgrid_service import send_email
import json
import logging
from datetime import datetime

# Initialize blueprint
user_bp = Blueprint('user', __name__)

@user_bp.route('/home')
@login_required
def home():
    try:
        # Verify user is authenticated
        if not current_user.is_authenticated:
            flash("Please log in to view your profile", "warning")
            return redirect(url_for('auth.login'))

        # Get user data with error handling
        user = User.query.get(current_user.id)
        if not user:
            flash("User profile not found", "error")
            return redirect(url_for('auth.login'))

        # Get future tournaments (after today's date)
        today = datetime.now().date()

        # Get all attending tournaments using the UserTournament model
        user_tournaments = UserTournament.query.filter_by(user_id=user.id).all()
        attending_ids = [ut.tournament_id for ut in user_tournaments]

        # Get all attending tournaments
        all_attending = Tournament.query.filter(Tournament.id.in_(attending_ids)).all() if attending_ids else []

        # Get user's past tournaments
        # Query the past_tournaments table directly
        past_tournaments_query = db.session.query(Tournament).join(
            past_tournaments,
            Tournament.id == past_tournaments.c.tournament_id
        ).filter(
            past_tournaments.c.user_id == user.id
        ).all()
        past_tournaments_attended = past_tournaments_query

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

        return render_template('profile.html', 
                            user=user, 
                            upcoming_tournaments=current_tournaments,
                            past_tournaments=past_tournaments_attended,
                            attendance_counts=attendance_counts)

    except Exception as e:
        # Add error handling to capture any other issues
        logging.error(f"Error in home route: {str(e)}")
        flash("An error occurred while loading your profile", "danger")
        return redirect(url_for('auth.login'))

# Keep the profile route for backward compatibility, redirecting to home
@user_bp.route('/profile')
@login_required
def profile():
    return render_template("profile.html", user=current_user)

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
            # Using only session_label instead of dates and sessions arrays
            session_label=None,
            open_to_meet=True,  # Default to being open to meeting
            wants_to_meet=True  # Also set wants_to_meet to True by default
        )
        db.session.add(new_registration)

    # Commit all changes
    db.session.commit()

    flash('Tournament preferences updated!', 'success')
    return redirect(url_for('user.home'))



@user_bp.route('/notifications/toggle', methods=['POST'])
@login_required
def toggle_notifications():
    current_user.notifications = not current_user.notifications
    db.session.commit()
    status = "enabled" if current_user.notifications else "disabled"
    flash(f'Notifications {status}!', 'success')
    return redirect(url_for('user.profile'))

@user_bp.route('/change_password', methods=['POST','GET'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Check if new password and confirmation match
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('user.change_password'))

        # Get the current user
        user = User.query.get(current_user.id)

        # If a current password was provided, verify it
        if current_password and user.password_hash:
            if not check_password_hash(user.password_hash, current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('user.change_password'))

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
    return render_template("change_password.html")

@user_bp.route('/my-tournaments')
@login_required
def my_tournaments():
    from models import Tournament, UserTournament

    user_tournaments = (
        db.session.query(UserTournament)
        .filter_by(user_id=current_user.id)
        .join(Tournament)
        .order_by(Tournament.start_date)
        .all()
    )

    return render_template("my_tournaments.html", user_tournaments=user_tournaments)

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

    if user.lanyard_ordered:
        return render_template('order_lanyard.html', lanyard_ordered=True, states=sorted(STATE_ABBRS))

    # Check if user has selected at least one session + opted in
    opted_in = db.session.query(UserTournament).filter_by(
        user_id=current_user.id,
        wants_to_meet=True
    ).count() > 0

    if not opted_in:
        flash("You need to select at least one tournament session and raise your hand before ordering your lanyard.")
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
            return render_template('order_lanyard.html', lanyard_ordered=False, states=sorted(STATE_ABBRS))

        # Update user in database to mark lanyard as ordered
        user.lanyard_ordered = True
        db.session.commit()

        # Send confirmation email to user
        if user.notifications:
            send_email(
                to_email=user.email,
                subject="Your CourtSide Club Lanyard Order",
                content_html=render_template('email/notification.html', 
                                            name=user.get_full_name(),
                                            message="Your lanyard order has been placed! You'll receive it soon.")
            )

        # Send admin notification
        admin_email = current_app.config.get('ADMIN_EMAIL')
        if admin_email:
            send_email(
                to_email=admin_email,
                subject="New Lanyard Order",
                content_html=render_template('email/admin_summary.html',
                                            user_email=user.email,
                                            user_name=user.get_full_name(),
                                            shipping_details=f"{name}, {address1}, {city}, {country}")
            )

        # Reload the page with the confirmation message
        return redirect(url_for('user.order_lanyard'))

    return render_template('order_lanyard.html', lanyard_ordered=False, states=sorted(STATE_ABBRS))