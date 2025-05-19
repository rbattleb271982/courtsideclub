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

# Shared helper function for consistent attendance and meetup counts
def get_tournament_attendance_stats(tournament_id, include_current_user=True):
    """
    Get consistent attendance statistics for a tournament
    
    Args:
        tournament_id: The ID of the tournament to get stats for
        include_current_user: Whether to include the current user in the counts
        
    Returns:
        Dict with keys 'attending' and 'meetup' containing the counts
    """
    from flask_login import current_user
    
    # Base query to get valid attendance records
    query = UserTournament.query.filter(
        UserTournament.tournament_id == tournament_id,
        UserTournament.attending == True
        # Removed session_label filters that were causing the "0 attending" issue
    )
    
    # Optionally exclude current user
    if not include_current_user and current_user.is_authenticated:
        query = query.filter(UserTournament.user_id != current_user.id)
    
    # Get all matching records
    attendances = query.all()
    
    # Calculate stats
    stats = {
        'attending': len(attendances),
        'meetup': sum(1 for a in attendances if a.wants_to_meet)
    }
    
    return stats

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
        # Get selected sessions
        selected_sessions = request.form.getlist('sessions')
        # Get wants_to_meet preference using standardized field name
        wants_to_meet_value = request.form.get('wants_to_meet')
        wants_to_meet = wants_to_meet_value == 'true' if wants_to_meet_value else False
        
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
    
    # Static override for demonstration - force inclusion of the current user
    # This ensures that we see at least 1 person attending if the user has selected sessions
    my_attending = False
    my_wants_to_meet = False
    
    # Check if the current user should be counted - must have session(s) selected
    if user_tournament and user_tournament.attending and user_tournament.session_label and user_tournament.session_label != '':
        my_attending = True
        my_wants_to_meet = user_tournament.wants_to_meet
        
    # Calculate total stats including the current user if they're attending with sessions
    attending_count = 1 if my_attending else 0
    # Only count as "open to meeting" if they have sessions selected AND wants_to_meet is True
    meetup_count = 1 if (my_attending and my_wants_to_meet) else 0
    lanyard_count = 1 if (my_attending and current_user.lanyard_ordered) else 0
    
    stats = {
        'attending': attending_count,
        'meetup': meetup_count,
        'lanyards': lanyard_count
    }
    
    print(f"DEBUG: Final stats: {stats}")
    
    # Count how many users are attending each session using Counter
    from collections import Counter
    
    # Get all user sessions for this tournament
    user_sessions = (
        db.session.query(UserTournament.session_label)
        .filter_by(tournament_id=tournament.id)
        .filter(UserTournament.attending == True)
        .filter(UserTournament.session_label.isnot(None))
        .filter(UserTournament.session_label != '')
        .all()
    )
    
    # Collect all individual session labels
    all_labels = []
    for ut in user_sessions:
        if ut.session_label:
            labels = [label.strip() for label in ut.session_label.split(',') if label.strip()]
            all_labels.extend(labels)
    
    # Count occurrences of each session
    session_counts = Counter(all_labels)
    
    # Make sure to count the current user's selections
    if user_tournament and user_tournament.attending and user_tournament.session_label:
        current_user_sessions = [s.strip() for s in user_tournament.session_label.split(',') if s.strip()]
        for session in current_user_sessions:
            session_counts[session] += 1
    
    # Add debugging to see what session_counts contains
    print(f"DEBUG: session_counts = {dict(session_counts)}")
    
    # Create session stats dictionary with actual counts
    session_stats = {}
    if tournament.sessions:
        for session in tournament.sessions:
            # Get the count directly from our Counter (already includes current user)
            attendee_count = session_counts.get(session, 0)
            
            # Store the count
            session_stats[session] = {
                'attendees': attendee_count
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
                         session_counts=session_counts,  # Add session_counts to template context
                         wants_to_meet=wants_to_meet,
                         user_attending=user_attending,
                         days_until=days_until,
                         session_saved=session_saved)

# Updated profile route to show user profile instead of redirecting
@user_bp.route('/profile')
@login_required
def profile():
    return render_template('user/profile.html', user=current_user)

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

@user_bp.route('/cancel_attendance/<tournament_id>', methods=['POST'])
@login_required
def cancel_attendance(tournament_id):
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament_id
    ).first()
    
    if user_tournament:
        db.session.delete(user_tournament)
        db.session.commit()
        flash("Your tournament attendance has been cancelled.", "success")

    return redirect(url_for('user.my_tournaments'))

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
    from datetime import datetime, timedelta
    import logging

    today = datetime.now().date()
    
    # Get all future tournaments the user is attending (regardless of session selection)
    # Log queries to debug tournament display issues
    logging.debug(f"Finding tournaments for user {current_user.id}")
    
    # First, check all user tournaments directly from database
    all_user_tournaments = UserTournament.query.filter_by(user_id=current_user.id).all()
    for ut in all_user_tournaments:
        logging.debug(f"Database record: Tournament: {ut.tournament_id}, Attending: {ut.attending}, Label: {ut.session_label}")
    
    # Query all tournaments to check dates
    all_tournaments = Tournament.query.all()
    for t in all_tournaments:
        if t.id == 'rome_masters' or t.id == 'geneva_open':
            logging.debug(f"Tournament dates check: {t.id}, Start: {t.start_date}, End: {t.end_date}, Days left: {(t.end_date - today).days}")
    
    # Now perform the filtered query for the page
    user_tournaments = (
        db.session.query(UserTournament)
        .filter(
            UserTournament.user_id == current_user.id,
            UserTournament.attending == True  # Keep only those marked as attending
        )
        .join(Tournament)
        .filter(Tournament.end_date >= today)  # Show tournaments ending today or in the future
        .order_by(Tournament.start_date)
        .all()
    )
    
    # Log more detailed information about what we found
    for ut in user_tournaments:
        logging.debug(f"Found for display: {ut.tournament.name}, session_label: {ut.session_label}")
    
    logging.debug(f"Found {len(user_tournaments)} tournaments to display")

    # Get stats for each tournament using shared helper function
    stats = {}
    session_stats = {}
    from collections import Counter
    from datetime import timedelta
    
    for ut in user_tournaments:
        tournament = ut.tournament
        # Use shared helper function to get consistent counts
        tournament_stats = get_tournament_attendance_stats(tournament.id, include_current_user=True)
        stats[tournament.id] = tournament_stats
        
        # Generate session stats by day
        # Get all session labels for this tournament
        user_sessions = (
            db.session.query(UserTournament.session_label)
            .filter(
                UserTournament.tournament_id == tournament.id,
                UserTournament.attending == True,
                UserTournament.session_label.isnot(None),
                UserTournament.session_label != ''
            )
            .all()
        )
        
        # Extract and count all session labels
        all_sessions = []
        for registration in user_sessions:
            if registration.session_label:
                sessions = [session.strip() for session in registration.session_label.split(',') if session.strip()]
                all_sessions.extend(sessions)
        
        # Count occurrences of each session
        session_counts = Counter(all_sessions)
        
        # Generate all days between tournament start and end dates
        tournament_days = []
        current_date = tournament.start_date
        day_num = 1
        
        while current_date <= tournament.end_date:
            day_key = f"Day {day_num}"
            day_session = f"{day_key} - Day"
            night_session = f"{day_key} - Night"
            
            tournament_days.append({
                'date': current_date,
                'day_num': day_num,
                'formatted': current_date.strftime('%A, %b %d'),
                'day_session': day_session,
                'night_session': night_session,
                'day_count': session_counts.get(day_session, 0),
                'night_count': session_counts.get(night_session, 0)
            })
            
            current_date += timedelta(days=1)
            day_num += 1
        
        # Store the days data for this tournament
        session_stats[tournament.id] = tournament_days

    # Group tournaments by month chronologically
    from collections import defaultdict
    from calendar import month_name

    grouped = defaultdict(list)
    month_keys = []

    for ut in user_tournaments:
        year_month = (ut.tournament.start_date.year, ut.tournament.start_date.month)
        grouped[year_month].append(ut)
        if year_month not in month_keys:
            month_keys.append(year_month)

    month_keys.sort()  # Sort chronologically by year and month

    # Create final grouped dictionary with formatted month names
    grouped_tournaments = {
        f"{month_name[month]} {year}": grouped[(year, month)]
        for (year, month) in month_keys
    }
    
    # Calculate lanyard reminder data
    show_lanyard_reminder = False
    days_away = None
    soonest_tournament = None
    
    # Only show lanyard reminder if user has tournaments with sessions AND hasn't ordered a lanyard
    if user_tournaments and not current_user.lanyard_ordered:
        show_lanyard_reminder = True
        # Find soonest upcoming tournament for days_away calculation
        soonest_tournament = min(user_tournaments, key=lambda ut: ut.tournament.start_date)
        days_away = (soonest_tournament.tournament.start_date - today).days

    return render_template(
        "my_tournaments.html",
        grouped_tournaments=grouped_tournaments,
        stats=stats,
        session_stats=session_stats,
        show_lanyard_reminder=show_lanyard_reminder,
        days_away=days_away,
        soonest_tournament=soonest_tournament.tournament if soonest_tournament else None
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
    
    # Sort months chronologically using month_order
    month_order = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    # Sort by year first, then by month
    sorted_months = sorted(grouped_tournaments.items(), key=lambda x: (
        int(x[0].split()[1]),  # Year (e.g., 2025)
        month_order[x[0].split()[0]]  # Month (e.g., August = 8)
    ))
    
    # Add attendance status to each tournament
    for month, month_group in sorted_months:
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
                    tournament.wants_to_meet = ut.wants_to_meet  # Pass wants_to_meet to template
                elif ut.attending and ut.attendance_type == 'maybe':
                    tournament.attendance_status = 'maybe'
                    tournament.has_sessions = bool(ut.session_label)  # They might have sessions
                    tournament.wants_to_meet = ut.wants_to_meet  # Pass wants_to_meet to template
                # Fall back to legacy logic for any records without attendance_type
                elif ut.attending and ut.session_label:
                    tournament.attendance_status = 'attending'
                    tournament.has_sessions = True
                    tournament.wants_to_meet = ut.wants_to_meet  # Pass wants_to_meet to template
                elif ut.attending and not ut.session_label:
                    tournament.attendance_status = 'maybe'
                    tournament.wants_to_meet = ut.wants_to_meet  # Pass wants_to_meet to template
            
            # Add stats to each tournament - need to count all attendees, including current user
            # We need to handle the case where the current user is attending but their attendance
            # isn't yet reflected in the database stats
            stats = get_tournament_attendance_stats(tournament.id, include_current_user=True)
            
            # If user is marked as attending this tournament in the UI but not counted in stats yet
            if tournament.attendance_status == 'attending' and tournament.has_sessions:
                # Count current user manually if they're attending with sessions
                tournament.attendee_count = stats['attending']
                # For meetup count, include current user if they want to meet
                if tournament.wants_to_meet:
                    tournament.meetup_count = stats['meetup']
                else:
                    tournament.meetup_count = stats['meetup']
            else:
                # Standard counting for tournaments user isn't attending
                tournament.attendee_count = stats['attending']
                tournament.meetup_count = stats['meetup']
    
    # Get list of months for filter bar (in correct chronological order)
    months = [month for month, _ in sorted_months]
    
    return render_template(
        "user/browse_tournaments.html",
        grouped_tournaments=dict(sorted_months),
        months=months,
        sorted_months=sorted_months
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