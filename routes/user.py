from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Tournament, UserTournament, UserPastTournament, ShippingAddress, UserWishlistTournament
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
        UserTournament.attending == True,
        UserTournament.session_label.isnot(None),  # Only count users who have selected sessions
        UserTournament.session_label != ''  # Make sure it's not an empty string
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
@user_bp.route('/tournaments/<tournament_slug>', methods=['GET', 'POST'])
@login_required
def tournament_detail(tournament_slug):
    print("="*50)
    print(f"TOURNAMENT DETAIL ROUTE ACCESSED: {tournament_slug}")
    print("="*50)
    print("ROUTE IS EXECUTING - CHECKING FOR ERRORS...")
    # Get the tournament by slug
    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
    
    # DEBUG: Check tournament sessions data
    print("DEBUG sessions =", getattr(tournament, 'sessions', None))
    print("DEBUG tournament.start_date =", tournament.start_date)
    print("DEBUG tournament.end_date =", tournament.end_date)
    
    # Get current user's tournament registration
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament.id
    ).first()
    
    # Process form submission for session selection
    if request.method == 'POST':
        attendance_type = request.form.get('status', 'not_attending')
        selected_sessions = request.form.getlist('sessions')
        wants_to_meet = request.form.get('wants_to_meet') == 'on'

        if not user_tournament:
            user_tournament = UserTournament()
            user_tournament.user_id = current_user.id
            user_tournament.tournament_id = tournament.id
            db.session.add(user_tournament)

        user_tournament.attendance_type = attendance_type
        user_tournament.attending = attendance_type in ['attending', 'maybe']
        user_tournament.wants_to_meet = wants_to_meet
        user_tournament.session_label = ','.join(selected_sessions)
        
        db.session.commit()
        flash("Your selections were saved.", "success")
        return redirect(url_for('user.tournament_detail', tournament_slug=tournament.slug))
    
    # Generate tournament days structure for the template
    from datetime import timedelta
    
    tournament_days = []
    current_date = tournament.start_date
    for day_num in range(1, (tournament.end_date - tournament.start_date).days + 2):
        tournament_days.append({
            "day_num": day_num,
            "formatted": current_date.strftime("%A, %B %d"),
            "date": current_date
        })
        current_date += timedelta(days=1)
    
    # Get selected sessions for the template
    selected_sessions = user_tournament.session_label.split(',') if user_tournament and user_tournament.session_label else []
    
    # DEBUG: Check tournament_days and selected_sessions
    print("DEBUG tournament_days =", tournament_days)
    print("DEBUG selected_sessions =", selected_sessions)
    
    # Get tournament stats using the shared helper function
    # Include current user to show accurate counts including themselves
    stats = get_tournament_attendance_stats(tournament.id, include_current_user=True)
    
    # Add lanyard count - only count users with session selections and lanyard ordered
    stats['lanyards'] = UserTournament.query.filter(
        UserTournament.tournament_id == tournament.id,
        UserTournament.attending == True,
        UserTournament.session_label.isnot(None),
        UserTournament.session_label != ''
    ).join(User).count()
    
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
    
    # Sort sessions alphabetically (case-insensitive) for better UX
    sorted_sessions = sorted(tournament.sessions, key=str.lower) if tournament.sessions else []
    
    # Create session stats dictionary with actual counts
    session_stats = {}
    if sorted_sessions:
        for session in sorted_sessions:
            # Get the count directly from our Counter (already includes current user)
            attendee_count = session_counts.get(session, 0)
            
            # Store the count
            session_stats[session] = {
                'attendees': attendee_count
            }
    
    # Calculate days until tournament
    today = datetime.now().date()
    days_until = (tournament.start_date - today).days if tournament.start_date > today else 0
    
    # Ensure tournament sessions data exists - create comprehensive day/night structure
    # Force regeneration if sessions are missing, incomplete, or not properly paired
    tournament_duration = (tournament.end_date - tournament.start_date).days + 1
    expected_session_count = tournament_duration * 2  # Day + Night for each day
    
    should_regenerate = (
        not tournament.sessions or 
        len(tournament.sessions) == 0 or
        len(tournament.sessions) % 2 != 0 or  # Odd number = incomplete pairs
        len(tournament.sessions) != expected_session_count  # Wrong total count
    )
    
    if should_regenerate:
        print(f"DEBUG: Regenerating sessions for {tournament.name}")
        print(f"DEBUG: Current sessions: {tournament.sessions}")
        print(f"DEBUG: Expected {expected_session_count} sessions for {tournament_duration} days")
        
        # Create complete Day/Night sessions for all tournament days
        default_sessions = []
        for day in range(1, tournament_duration + 1):
            default_sessions.extend([
                f'Day {day} - Day',
                f'Day {day} - Night'
            ])
        
        # Update the database with complete session structure
        tournament.sessions = default_sessions
        db.session.commit()
        print(f"DEBUG: Regenerated {len(default_sessions)} sessions: {tournament.sessions}")
    else:
        print(f"DEBUG: Tournament sessions from DB are complete: {tournament.sessions}")
    
    # Ensure session stats exist for all sessions
    for session in tournament.sessions:
        if session not in session_stats:
            session_stats[session] = {
                'attendees': 0  # Default count if no data
            }
    
    # Calculate tournament_days using the correct format for session checkboxes
    from datetime import timedelta
    
    tournament_days = []
    current_date = tournament.start_date
    for day_num in range(1, (tournament.end_date - tournament.start_date).days + 2):
        tournament_days.append({
            "day_num": day_num,
            "formatted": current_date.strftime("%A, %B %d"),
            "date": current_date
        })
        current_date += timedelta(days=1)
    
    print(f"DEBUG: Created tournament_days structure with {len(tournament_days)} days")
    print(f"DEBUG: tournament_days = {tournament_days}")
    
    # Check if sessions were just saved (from query param)
    session_saved = request.args.get('session_saved', '0') == '1'
    
    # CRITICAL DEBUG - CHECK TEMPLATE CONDITIONALS
    print("="*80)
    print("TEMPLATE CONDITIONAL DEBUG:")
    print(f"user_attending = {user_attending} (type: {type(user_attending)})")
    print(f"user_attending evaluates to: {bool(user_attending)}")
    print(f"tournament.sessions = {tournament.sessions}")
    print(f"tournament_days length = {len(tournament_days) if tournament_days else 0}")
    print(f"session_counts = {session_counts}")
    print(f"Template will show session UI: {bool(user_attending)}")
    if user_tournament:
        print(f"UserTournament exists: attending={user_tournament.attending}")
    else:
        print("No UserTournament record found")
    print("="*80)
    
    # Get past tournaments for users attending this tournament (shared-history logic)
    shared_past_tournaments = {}
    
    # If user is authenticated, show them past tournaments whether other attendees exist or not
    if current_user.is_authenticated and current_user.id:
        # Get current user's past tournaments (excluding current tournament)
        user_past_tournaments = db.session.query(
            Tournament.name
        ).join(
            UserPastTournament, Tournament.id == UserPastTournament.tournament_id
        ).filter(
            UserPastTournament.user_id == current_user.id,
            Tournament.id != tournament.id  # Exclude current tournament
        ).all()
        
        # Format the results as a dictionary with count=1 for each tournament
        shared_past_tournaments = {name: 1 for name, in user_past_tournaments}
        
        # Now get additional attendees' past tournaments (if any)
        other_attendees = db.session.query(UserTournament.user_id).filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.attending == True,
            UserTournament.user_id != current_user.id  # Exclude current user
        ).all()
        
        other_attendee_ids = [user.user_id for user in other_attendees]
        
        if other_attendee_ids:
            # Get past tournaments for other attendees
            other_past_tournament_counts = db.session.query(
                Tournament.name, db.func.count(UserPastTournament.user_id).label('count')
            ).join(
                UserPastTournament, Tournament.id == UserPastTournament.tournament_id
            ).filter(
                UserPastTournament.user_id.in_(other_attendee_ids),
                Tournament.id != tournament.id  # Exclude current tournament
            ).group_by(
                Tournament.name
            ).all()
            
            # Update counts in the shared dictionary
            for name, count in other_past_tournament_counts:
                if name in shared_past_tournaments:
                    shared_past_tournaments[name] += count
                else:
                    shared_past_tournaments[name] = count
    
    # Convert to sorted list of tuples for template rendering - alphabetically by tournament name (case-insensitive)
    sorted_shared_tournaments = sorted(shared_past_tournaments.items(), key=lambda x: x[0].lower())
    
    print(f"DEBUG: shared_past_tournaments = {shared_past_tournaments}")
    print(f"DEBUG: sorted_shared_tournaments = {sorted_shared_tournaments}")
    print(f"DEBUG: len(sorted_shared_tournaments) = {len(sorted_shared_tournaments)}")
    
    # Generate sample members data for v0 layout
    sample_members = []
    attending_users = UserTournament.query.filter_by(
        tournament_id=tournament.id, 
        attending=True
    ).join(User).limit(8).all()
    
    for ut in attending_users:
        user = ut.user
        if user and not user.test_user:  # Exclude test users from display
            # Count sessions for this user
            session_count = len(ut.session_label.split(',')) if ut.session_label else 0
            
            # Generate initials
            first_initial = user.first_name[0].upper() if user.first_name else 'U'
            last_initial = user.last_name[0].upper() if user.last_name else 'U'
            initials = first_initial + last_initial
            
            # Create display name (first name + last initial)
            display_name = f"{user.first_name} {last_initial}." if user.first_name and user.last_name else f"User {user.id}"
            
            sample_members.append({
                'initials': initials,
                'display_name': display_name,
                'session_count': session_count,
                'open_to_meet': bool(ut.wants_to_meet)
            })
    
    # Generate fan history data (top 3-5 tournaments these users have attended)
    fan_history = []
    if attending_users:
        # Get other tournaments that these users have attended
        user_ids = [ut.user_id for ut in attending_users]
        other_tournaments = db.session.query(Tournament.name, db.func.count(UserTournament.user_id).label('count')).join(
            UserTournament
        ).filter(
            UserTournament.user_id.in_(user_ids),
            UserTournament.attending == True,
            Tournament.id != tournament.id
        ).group_by(Tournament.name).order_by(
            db.func.count(UserTournament.user_id).desc()
        ).limit(5).all()
        
        fan_history = [{'name': name} for name, count in other_tournaments]
    
    # Calculate tournament stats
    stats = get_tournament_attendance_stats(tournament.id, include_current_user=True)
    
    # Calculate session counts
    session_counts = {}
    all_user_tournaments = UserTournament.query.filter_by(
        tournament_id=tournament.id,
        attending=True
    ).all()
    
    for ut in all_user_tournaments:
        if ut.session_label:
            sessions = [s.strip() for s in ut.session_label.split(',') if s.strip()]
            for session in sessions:
                session_counts[session] = session_counts.get(session, 0) + 1
    
    # Calculate days until tournament
    from datetime import date
    days_until = (tournament.start_date - date.today()).days
    
    # Get shared history for template
    shared_history = []
    
    # DEBUG DUMP - Show runtime values
    print('tournament_days:', len(tournament_days), tournament_days)
    print('session_label:', user_tournament.session_label if user_tournament else None)
    print('selected_sessions:', selected_sessions)
    print('Template variables passed:')
    print('tournament:', tournament.slug)
    print('days_until:', (tournament.start_date - date.today()).days)
    print('user_attending:', user_tournament.attending if user_tournament else None)
    print('attendance_type:', user_tournament.attendance_type if user_tournament else None)
    print('attending_count:', stats['attending'])
    print('meeting_count:', stats['meetup'])
    print('session_counts:', session_counts)
    
    return render_template('tournament_detail.html',
                         tournament=tournament,
                         tournament_days=tournament_days,
                         selected_sessions=selected_sessions,
                         user_tournament=user_tournament,
                         wants_to_meet=user_tournament.wants_to_meet if user_tournament else True,
                         is_attending=user_tournament.attendance_type == 'attending' if user_tournament else False,
                         is_maybe=user_tournament.attendance_type == 'maybe' if user_tournament else False,
                         is_not_attending=user_tournament.attendance_type == 'not_attending' if user_tournament else True,
                         user_attending=user_tournament.attending if user_tournament else False,
                         attending_count=stats['attending'],
                         meeting_count=stats['meetup'],
                         session_counts=session_counts,
                         days_until=days_until,
                         shared_history=shared_history)

# Updated profile route to show user profile with past tournaments selection
@user_bp.route('/add_wishlist', methods=['POST'])
@login_required
def add_wishlist():
    """Add a tournament to user's bucket list (wishlist)"""
    tournament_id = request.form.get('tournament_id')
    if not tournament_id:
        flash('Tournament selection required', 'warning')
        return redirect(url_for('user.profile'))
        
    # Check if already in wishlist
    existing = UserWishlistTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament_id
    ).first()
    
    if not existing:
        # Add to wishlist
        entry = UserWishlistTournament(
            user_id=current_user.id,
            tournament_id=tournament_id
        )
        db.session.add(entry)
        db.session.commit()
        
        # Log the event
        log_event(current_user.id, 'wishlist_tournament_added', {
            'tournament_id': tournament_id
        })
        
        # Get tournament name for the flash message
        tournament = Tournament.query.get(tournament_id)
        if tournament:
            flash(f'Added {tournament.name} to your bucket list!', 'success')
        else:
            flash('Tournament added to your bucket list!', 'success')
    else:
        flash('Tournament is already in your bucket list', 'info')
        
    return redirect(url_for('user.profile'))
    
@user_bp.route('/remove_wishlist/<int:wishlist_id>', methods=['POST'])
@login_required
def remove_wishlist(wishlist_id):
    """Remove a tournament from user's bucket list (wishlist)"""
    entry = UserWishlistTournament.query.filter_by(
        id=wishlist_id,
        user_id=current_user.id
    ).first()
    
    if entry:
        tournament_id = entry.tournament_id
        
        # Get tournament name for the flash message
        tournament = Tournament.query.get(tournament_id)
        tournament_name = tournament.name if tournament else "Tournament"
        
        # Remove from database
        db.session.delete(entry)
        db.session.commit()
        
        # Log the event
        log_event(current_user.id, 'wishlist_tournament_removed', {
            'tournament_id': tournament_id
        })
        
        flash(f'Removed {tournament_name} from your bucket list', 'success')
    else:
        flash('Tournament not found in your bucket list', 'warning')
        
    return redirect(url_for('user.profile'))

@user_bp.route('/update_wishlist', methods=['POST'])
@login_required
def update_wishlist():
    """Update the user's bucket list of tournaments"""
    # Get the list of tournament IDs from the form
    tournament_ids = request.form.getlist('wishlist_tournaments')
    
    # First, remove all existing wishlist entries for this user
    UserWishlistTournament.query.filter_by(user_id=current_user.id).delete()
    
    # Now add the new selections
    for tournament_id in tournament_ids:
        wishlist_entry = UserWishlistTournament(
            user_id=current_user.id,
            tournament_id=tournament_id
        )
        db.session.add(wishlist_entry)
    
    # Save changes
    db.session.commit()
    
    # Log the event
    log_event(current_user.id, 'wishlist_updated', {
        'count': len(tournament_ids),
        'tournament_ids': tournament_ids
    })
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Bucket list updated!'})
    
    flash('Your bucket list has been updated!', 'success')
    return redirect(url_for('user.profile'))

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    from forms import ProfileForm
    
    form = ProfileForm()
    all_tournaments = Tournament.query.order_by(Tournament.name).all()

    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.notifications = form.notifications.data

        attended_ids = request.form.getlist('attended_tournaments[]')
        wishlist_ids = request.form.getlist('wishlist_tournaments[]')

        db.session.query(UserPastTournament).filter_by(user_id=current_user.id).delete()
        db.session.query(UserWishlistTournament).filter_by(user_id=current_user.id).delete()

        for tid in attended_ids:
            db.session.add(UserPastTournament(user_id=current_user.id, tournament_id=int(tid)))
        for tid in wishlist_ids:
            db.session.add(UserWishlistTournament(user_id=current_user.id, tournament_id=int(tid)))

        db.session.commit()
        flash("Your profile has been updated.", "success")
        return redirect(url_for('user.profile'))

    # Pre-populate form with current user data
    form.first_name.data = current_user.first_name
    form.last_name.data = current_user.last_name
    # Default notifications to True if user hasn't set a preference yet
    form.notifications.data = current_user.notifications if current_user.notifications is not None else True

    past_ids = [t.tournament_id for t in current_user.past_tournaments]
    wishlist_ids = [w.tournament_id for w in current_user.wishlist]

    return render_template(
        'user/profile.html',
        user=current_user,
        form=form,
        past_tournaments=all_tournaments,
        attended_ids=past_ids,
        wishlist_ids=wishlist_ids,
    )

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
    
    # Track location updates
    if location_changed:
        event_data['location_updated'] = True
        event_data['new_location'] = location
    
    # Track notification preference changes
    if 'notifications' in request.form:
        # Check if the notification setting actually changed
        if notifications != getattr(user, 'notifications', None):
            event_data['notification_preference_changed'] = True
            event_data['notifications_enabled'] = notifications
            
            # Log a specific notification preference event for better analytics
            notification_event = 'user_opt_in_email' if notifications else 'user_opt_out_email'
            log_event(current_user.id, notification_event, data={
                'email': current_user.email,
                'timestamp': datetime.utcnow().isoformat()
            })
            
    log_event(current_user.id, 'profile_updated', data=event_data)

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
    try:
        # Simple approach: just mark as not attending instead of deleting
        # This prevents any potential session conflicts from database deletions
        user_tournament = UserTournament.query.filter_by(
            user_id=current_user.id, 
            tournament_id=tournament_id
        ).first()

        if not user_tournament:
            flash("Could not find your attendance record.", "warning")
        else:
            # Instead of deleting, just mark as not attending
            user_tournament.attending = False
            user_tournament.session_label = None
            user_tournament.wants_to_meet = False
            db.session.commit()
            flash("Your attendance has been cancelled.", "success")
        
    except Exception as e:
        print(f"Cancel attendance error: {e}")
        db.session.rollback()
        flash("Unable to cancel attendance. Please try again.", "danger")

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

    # Debug session persistence
    logging.info(f"=== MY_TOURNAMENTS ROUTE ACCESS ===")
    logging.info(f"current_user.is_authenticated: {current_user.is_authenticated}")
    logging.info(f"current_user object: {current_user}")
    logging.info(f"Session contents: {dict(session)}")
    logging.info(f"Request cookies: {dict(request.cookies)}")
    
    if not current_user.is_authenticated:
        logging.info(f"User not authenticated, redirecting to login")
        return redirect(url_for('auth.login'))

    # Check for welcome message flag in session
    show_welcome = session.pop('show_welcome', False)
    
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
    
    # Only show lanyard reminder if user is attending tournaments but hasn't selected sessions properly
    # Note: lanyard_ordered functionality discontinued, always check for incomplete tournaments
    # Check for users attending tournaments but missing proper session selections
    incomplete_tournaments = []
    for ut in user_tournaments:
        if ut.attending and (not ut.session_label or ut.session_label.strip() == ''):
            incomplete_tournaments.append(ut)
    
    if incomplete_tournaments:
        show_lanyard_reminder = True
        # Find soonest upcoming tournament for days_away calculation
        soonest_tournament = min(incomplete_tournaments, key=lambda ut: ut.tournament.start_date)
        days_away = (soonest_tournament.tournament.start_date - today).days

    # Check if user needs profile reminder (no past tournaments AND no wishlist)
    show_profile_reminder = (
        len(current_user.past_tournaments) == 0 and
        len(current_user.wishlist) == 0
    )

    return render_template(
        "my_tournaments.html",
        grouped_tournaments=grouped_tournaments,
        stats=stats,
        session_stats=session_stats,
        show_lanyard_reminder=show_lanyard_reminder,
        days_away=days_away,
        soonest_tournament=soonest_tournament.tournament if soonest_tournament else None,
        show_welcome=show_welcome,
        show_profile_reminder=show_profile_reminder
    )

@user_bp.route('/add-tournaments')
@login_required
def add_tournaments():
    """
    Redirect users to browse tournaments page where they can add tournaments to their schedule.
    This route exists for onboarding flow clarity.
    """
    return redirect(url_for('user.browse_tournaments'))

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
                tournament.meeting_count = stats['meetup']
            else:
                # Standard counting for tournaments user isn't attending
                tournament.attendee_count = stats['attending']
                tournament.meeting_count = stats['meetup']
    
    # Get list of months for filter bar (in correct chronological order)
    months = [month for month, _ in sorted_months]
    
    return render_template(
        "user/browse_tournaments.html",
        grouped_tournaments=dict(sorted_months),
        months=months,
        sorted_months=sorted_months
    )

@user_bp.route('/lanyard', methods=['GET', 'POST'])
@login_required
def lanyard():

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
        # Check if user has valid sessions using proper database query
        has_valid_sessions = (
            db.session.query(UserTournament)
            .filter(
                UserTournament.user_id == current_user.id,
                UserTournament.attending == True,
                UserTournament.session_label.isnot(None),
                UserTournament.session_label != ""
            )
            .count() > 0
        )

        if not has_valid_sessions:
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
            zip_code=request.form['zip'],
            country=request.form['country']
        )

        # Lanyard ordering functionality discontinued - no need to update user status

        # Save to database
        db.session.add(address)
        db.session.commit()

        # Lanyard order confirmation email removed - functionality discontinued

        # Log the lanyard order event - temporarily disabled due to event name issue
        print(f"DEBUG: Lanyard order placed for user {current_user.id}, name: {request.form['name']}, country: {request.form['country']}")
        
        # Flash success message and redirect to My Tournaments
        flash("You're all set! See you at the tournament.", "success")
        return redirect(url_for('user.my_tournaments'))

    # Check if user has an existing shipping address (indicates previous lanyard order)
    existing_address = ShippingAddress.query.filter_by(user_id=current_user.id).first()
    has_existing_address = existing_address is not None
    
    return render_template('order_lanyard.html', 
                         states=sorted(STATE_ABBRS),
                         has_existing_address=has_existing_address)