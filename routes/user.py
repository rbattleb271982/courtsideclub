from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Tournament, UserTournament, past_tournaments, ShippingAddress
from services.sendgrid_service import send_email
from services.event_logger import log_event
import json
import logging
from datetime import datetime

# Initialize blueprint
user_bp = Blueprint('user', __name__)

# Home route removed - users now go directly to my_tournaments
@user_bp.route('/home')
@login_required
def home():
    return redirect(url_for('user.my_tournaments'))
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

# Tournament detail view specifically for logged-in users
@user_bp.route('/tournament/<tournament_slug>', methods=['GET', 'POST'])
@login_required
def tournament_detail(tournament_slug):
    # Get the tournament by slug
    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
    
    # Process form submission for session selection
    if request.method == 'POST':
        # Get selected sessions and wants_to_meet preference (from either top or bottom checkbox)
        selected_sessions = request.form.getlist('sessions')
        # Check for wants_to_meet from either the top section or the form section
        wants_to_meet = bool(request.form.get('wants-to-meet-top', False)) or bool(request.form.get('wants_to_meet', False))
        
        # Get or create user tournament registration
        user_tournament = UserTournament.query.filter_by(
            user_id=current_user.id, 
            tournament_id=tournament.id
        ).first()
        
        if not user_tournament:
            # Create a new UserTournament record
            user_tournament = UserTournament()
            user_tournament.user_id = current_user.id
            user_tournament.tournament_id = tournament.id
            db.session.add(user_tournament)
        
        # Only mark as attending if they selected at least one session
        if selected_sessions:
            user_tournament.attending = True
        else:
            # If no sessions selected but form submitted, keep current attending status
            # This allows users to update wants_to_meet without losing attendance status
            if user_tournament.attending is None:
                user_tournament.attending = False
            
        user_tournament.wants_to_meet = wants_to_meet
        user_tournament.session_label = ','.join(selected_sessions) if selected_sessions else None
        
        # Log the event for tracking
        event_data = {
            'tournament_id': tournament.id,
            'tournament_name': tournament.name,
            'selected_sessions': selected_sessions,
            'wants_to_meet': wants_to_meet,
            'attending': user_tournament.attending
        }
        log_event(current_user.id, 'tournament_session_update', event_data)
        
        db.session.commit()
        
        flash('Your tournament sessions have been saved.', 'success')
        return redirect(url_for('user.tournament_detail', tournament_slug=tournament_slug, session_saved=1))
    
    # Get current user's tournament registration
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament.id
    ).first()
    
    # Get selected sessions for current user
    selected_sessions = []
    wants_to_meet = False
    user_attending = False
    
    print(f"DEBUG: user_tournament = {user_tournament}")
    if user_tournament:
        # Ensure attendance is properly set (might be None in some cases)
        if user_tournament.attending is None:
            user_tournament.attending = True
            db.session.commit()
            print("DEBUG: Fixed null attending value to True")
        
        user_attending = user_tournament.attending
        wants_to_meet = user_tournament.wants_to_meet if user_tournament.wants_to_meet is not None else False
        print(f"DEBUG: user_attending = {user_attending}, wants_to_meet = {wants_to_meet}")
        print(f"DEBUG: tournament.sessions = {tournament.sessions}")
        if user_tournament.session_label:
            selected_sessions = user_tournament.session_label.split(',')
            print(f"DEBUG: selected_sessions = {selected_sessions}")
    
    # Get tournament stats - include the current user for their own page
    # This allows users to see themselves in the counts right after saving
    
    # First get all attending users including the current user
    # Only count users who are attending AND have selected at least one session
    attending_users = UserTournament.query.filter(
        UserTournament.tournament_id == tournament.id,
        UserTournament.attending == True,
        UserTournament.session_label.isnot(None),
        UserTournament.session_label != ''
    ).all()
    
    # Debug output to verify
    attendee_ids = [ut.user_id for ut in attending_users]
    print(f"DEBUG: All attendee IDs: {attendee_ids}")
    print(f"DEBUG: Current user ID: {current_user.id}")
    
    # Calculate stats with current user included, but only if they've selected sessions
    stats = {
        'attending': len(attending_users),
        'meetup': UserTournament.query.filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.attending == True,
            UserTournament.wants_to_meet == True,
            UserTournament.session_label.isnot(None),
            UserTournament.session_label != ''
        ).count(),
        'lanyards': UserTournament.query.filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.attending == True,
            UserTournament.session_label.isnot(None),
            UserTournament.session_label != ''
        ).join(User).filter_by(lanyard_ordered=True).count()
    }
    
    print(f"DEBUG: Final stats: {stats}")
    
    # Get session-specific stats
    session_stats = {}
    if tournament.sessions:
        for session in tournament.sessions:
            # Count users attending this specific session - including current user
            # Only count those who have selected at least one session
            session_attendees = UserTournament.query.filter(
                UserTournament.tournament_id == tournament.id,
                UserTournament.attending == True,
                UserTournament.session_label.isnot(None),
                UserTournament.session_label != '',
                UserTournament.session_label.like(f'%{session}%')
            ).count()
            
            session_stats[session] = {
                'attendees': session_attendees
            }
    
    # Calculate days until tournament
    today = datetime.now().date()
    days_until = (tournament.start_date - today).days if tournament.start_date > today else 0
    
    # Ensure tournament sessions data exists
    if not tournament.sessions or len(tournament.sessions) == 0:
        # Add test sessions data if none exists
        default_sessions = [
            'Day 1 - Day', 
            'Day 1 - Night', 
            'Day 2 - Day', 
            'Day 2 - Night',
            'Day 3 - Day'
        ]
        # Update the database with these sessions
        tournament.sessions = default_sessions
        db.session.commit()
        print(f"DEBUG: Added default sessions to tournament {tournament.name}: {tournament.sessions}")
    else:
        print(f"DEBUG: Tournament sessions from DB: {tournament.sessions}")
    
    # Ensure session stats exist for all sessions
    for session in tournament.sessions:
        if session not in session_stats:
            session_stats[session] = {
                'attendees': 0  # Default count if no data
            }
    
    # Calculate dates for each tournament day
    # Use only imports already available at top of file
    import datetime as dt
    day_dates = []
    start_date = tournament.start_date
    for i in range(7):  # Generate 7 days of dates
        day_date = start_date + dt.timedelta(days=i)
        day_dates.append({
            'day_number': i + 1,
            'date': day_date,
            'formatted': day_date.strftime('%b %d')
        })
    
    # Check if sessions were just saved (from query param)
    session_saved = request.args.get('session_saved', '0') == '1'
    
    return render_template('user/tournament_detail.html',
                          day_dates=day_dates,
                         tournament=tournament,
                         user_tournament=user_tournament,
                         stats=stats,
                         attending_count=stats['attending'],
                         meeting_count=stats['meetup'],
                         selected_sessions=selected_sessions,
                         session_stats=session_stats,
                         wants_to_meet=wants_to_meet,
                         user_attending=user_attending,
                         days_until=days_until,
                         session_saved=session_saved)

# Keep the profile route for backward compatibility, redirecting to my_tournaments
@user_bp.route('/profile')
@login_required
def profile():
    return redirect(url_for('user.my_tournaments'))

@user_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    location = request.form.get('location')
    notifications = 'notifications' in request.form

    # Update user in database
    user = User.query.get(current_user.id)
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name

    # Track if location was updated
    location_changed = False
    if location is not None and location != user.location:
        user.location = location
        location_changed = True

    # Also update the name field for backward compatibility
    if first_name and last_name:
        user.name = f"{first_name} {last_name}"

    user.notifications = notifications
    db.session.commit()

    # Log the profile update event
    from services.event_logger import log_event
    event_data = {}
    if location_changed:
        event_data['location_updated'] = True
        event_data['new_location'] = location
    log_event(current_user.id, 'profile_updated', event_data)

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

        return redirect(url_for('user.profile'))
    return render_template("change_password.html")

@user_bp.route('/my-tournaments')
@login_required
def my_tournaments():
    from models import Tournament, UserTournament
    from datetime import datetime

    today = datetime.now().date()
    
    # Get future tournaments the user is registered for
    user_tournaments = (
        db.session.query(UserTournament)
        .filter_by(user_id=current_user.id, attending=True)
        .join(Tournament)
        .filter(Tournament.start_date >= today)
        .order_by(Tournament.start_date)
        .all()
    )

    # Get stats for each tournament
    stats = {}
    for ut in user_tournaments:
        tournament = ut.tournament
        # Only count other attendees
        registrations = UserTournament.query.filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.user_id != current_user.id
        ).all()
        stats[tournament.id] = {
            'attending': sum(1 for r in registrations if r.attending),
            'meetup': sum(1 for r in registrations if r.attending and r.wants_to_meet),
            'lanyards': sum(1 for r in registrations if r.attending and r.session_label)
        }

    # Group tournaments by month
    from itertools import groupby
    from datetime import datetime
    
    def get_month_key(ut):
        return ut.tournament.start_date.strftime('%B %Y')
    
    grouped_tournaments = {}
    sorted_tournaments = sorted(user_tournaments, key=get_month_key)
    for month, group in groupby(sorted_tournaments, key=get_month_key):
        grouped_tournaments[month] = list(group)

    return render_template(
        "my_tournaments.html",
        grouped_tournaments=grouped_tournaments,
        stats=stats
    )

@user_bp.route('/browse-tournaments')
@login_required
def browse_tournaments():
    """
    Display upcoming tournaments grouped by month with attendance status for the current user.
    Allow users to mark themselves as attending or maybe attending.
    """
    # Get today's date for filtering
    today = datetime.now().date()
    
    # Get all upcoming tournaments, sorted by start date
    upcoming_tournaments = Tournament.query.filter(
        Tournament.end_date >= today
    ).order_by(Tournament.start_date).all()
    
    # Get current user's tournament registrations
    user_registrations = {
        ut.tournament_id: ut for ut in UserTournament.query.filter_by(
            user_id=current_user.id
        ).all()
    }
    
    # Group tournaments by month
    def get_month_key(tournament):
        return tournament.start_date.strftime('%B %Y')
    
    grouped_tournaments = {}
    sorted_tournaments = sorted(upcoming_tournaments, key=get_month_key)
    
    from itertools import groupby
    for month, group in groupby(sorted_tournaments, key=get_month_key):
        grouped_tournaments[month] = list(group)
    
    # Add attendance status to each tournament
    for month_group in grouped_tournaments.values():
        for tournament in month_group:
            # Default status
            tournament.attendance_status = 'not_attending'
            tournament.has_sessions = False
            
            # If user has a registration, check the status
            if tournament.id in user_registrations:
                ut = user_registrations[tournament.id]
                if ut.attending and ut.attendance_type == 'attending':
                    tournament.attendance_status = 'attending'
                    tournament.has_sessions = bool(ut.session_label)  # Track if they have sessions
                elif ut.attending and ut.attendance_type == 'maybe':
                    tournament.attendance_status = 'maybe'
                    tournament.has_sessions = bool(ut.session_label)  # They might have sessions
                # Fall back to legacy logic for any records without attendance_type
                elif ut.attending and ut.session_label:
                    tournament.attendance_status = 'attending'
                    tournament.has_sessions = True
                elif ut.attending and not ut.session_label:
                    tournament.attendance_status = 'maybe'
            
            # Add stats to each tournament
            tournament.attendee_count = UserTournament.query.filter(
                UserTournament.tournament_id == tournament.id,
                UserTournament.attending == True,
                UserTournament.user_id != current_user.id  # Exclude current user
            ).count()
            
            tournament.meetup_count = UserTournament.query.filter(
                UserTournament.tournament_id == tournament.id,
                UserTournament.attending == True,
                UserTournament.wants_to_meet == True,
                UserTournament.user_id != current_user.id  # Exclude current user
            ).count()
    
    # Get list of months for filter bar
    months = list(grouped_tournaments.keys())
    
    return render_template(
        "user/browse_tournaments.html",
        grouped_tournaments=grouped_tournaments,
        months=months
    )

@user_bp.route('/lanyard')
@login_required
def lanyard():
    # Check if user has selected any tournament sessions
    attending_sessions = UserTournament.query.filter_by(
        user_id=current_user.id,
        attending=True
    ).first()

    if not attending_sessions or not attending_sessions.session_label:
        flash("To order your lanyard, you need to select a tournament and session first.", "warning")
        return redirect(url_for("user.my_tournaments"))

    # List of U.S. state abbreviations
    STATE_ABBRS = [
        "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI", "IA", "ID", "IL", "IN",
        "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ",
        "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA",
        "WI", "WV", "WY"
    ]

    # Debug: Print user sessions info
    user_sessions = UserTournament.query.filter_by(user_id=current_user.id).all()
    print(f"User {current_user.id} sessions:")
    for session in user_sessions:
        print(f"Tournament: {session.tournament_id}, Attending: {session.attending}, Label: {session.session_label}")

    # Allow admins to bypass session check
    if not current_user.is_admin:
        # Only allow access if user has selected at least one session and is marked as attending
        attending_sessions = UserTournament.query.filter_by(
            user_id=current_user.id,
            attending=True
        ).all()
        has_session = any(ut.session_label for ut in attending_sessions)

        if not has_session:
            flash("You must select at least one tournament session before ordering a lanyard.", "warning")
            return redirect(url_for('user.my_tournaments'))

    if request.method == 'POST':
        # Handle lanyard form submission
        address = ShippingAddress(
            user_id=current_user.id,
            name=request.form['name'],
            address1=request.form['address1'],
            address2=request.form.get('address2', ''),
            city=request.form['city'],
            state=request.form['state'],
            zip_code=request.form['zip_code'],
            country=request.form['country']
        )

        # Update user lanyard_ordered status
        current_user.lanyard_ordered = True

        # Save to database
        db.session.add(address)
        db.session.commit()

        flash("Lanyard request received! It will ship soon.")
        return redirect(url_for('user.profile'))

    return render_template('order_lanyard.html', 
                         states=sorted(STATE_ABBRS),
                         lanyard_ordered=current_user.lanyard_ordered)