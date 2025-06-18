from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Tournament, UserTournament, User, UserPastTournament
import datetime
from services.event_logger import log_event
from collections import Counter

tournaments_bp = Blueprint('tournaments', __name__)

@tournaments_bp.route("/tournaments")
@login_required
def list_tournaments():
    # Get all tournaments for dropdown options, sorted by name for the filter dropdown
    all_tournaments = Tournament.query.order_by(Tournament.name).all()

    # Get today's date for filtering
    today = datetime.datetime.now().date()

    # Initialize query with chronological sorting by start date and filter out past tournaments
    query = Tournament.query.filter(Tournament.end_date >= today).order_by(Tournament.start_date)

    # Get filter parameters
    name_filter = request.args.get('name')
    country_filter = request.args.get('country')

    # Apply name filter if provided
    if name_filter:
        query = query.filter(Tournament.id == name_filter)

    # Apply country filter if provided
    if country_filter:
        query = query.filter(Tournament.country == country_filter)

    # Get the filtered tournaments, in chronological order by start date
    tournaments = query.all()

    # Add stats to each tournament - exclude current user from counts consistently
    # Only calculate these stats once and use the same values everywhere
    
    attendance_counts = {}
    for tournament in tournaments:
        # Always exclude the current user from browse page stats for consistency
        # Count users who are attending (excluding current user)
        tournament.attendee_count = UserTournament.query.filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.attending == True,
            UserTournament.user_id != current_user.id
        ).count()

        # Count users who are open to meeting (excluding current user)
        tournament.hand_raised_count = UserTournament.query.filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.attending == True,
            UserTournament.wants_to_meet == True, 
            UserTournament.user_id != current_user.id
        ).count()

        # Count users who ordered lanyards (excluding current user)
        tournament.lanyard_count = UserTournament.query.filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.attending == True,
            UserTournament.user_id != current_user.id
        ).count()  # Lanyard functionality discontinued
        
        # Store consistent stats in the attendance_counts dictionary
        attendance_counts[tournament.id] = {
            'attending': tournament.attendee_count,
            'meeting': tournament.hand_raised_count
        }

    # Get today's date for highlighting current tournaments
    today = datetime.datetime.now().date()

    return render_template('tournaments.html',
                          tournaments=tournaments,
                          all_tournaments=all_tournaments,
                          today=today,
                          name_filter=name_filter,
                          country_filter=country_filter,
                          attendance_counts=attendance_counts)


# DISABLED - This route was conflicting with user.tournament_detail
# @tournaments_bp.route('/tournaments_admin/<tournament_slug>', methods=['GET', 'POST'])
# @login_required
# def view_tournament(tournament_slug):
    
    # Get current user's tournament registration
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament.id
    ).first()
    
    # Handle attendance parameter from browse tournaments page
    attendance_param = request.args.get('attendance')
    # Check if session_saved is in parameters (after saving sessions)
    session_saved = request.args.get('session_saved') == '1'
    
    # If we have an attendance parameter and no existing registration,
    # create one with the requested status
    if attendance_param and not user_tournament:
        # Create basic UserTournament record
        user_tournament = UserTournament()
        user_tournament.user_id = current_user.id
        user_tournament.tournament_id = tournament.id
        
        # Set attendance based on parameter, but don't pre-select sessions
        if attendance_param == 'attending':
            user_tournament.attending = True
            # No default session - user must explicitly select
            user_tournament.session_label = None

        elif attendance_param == 'maybe':
            user_tournament.attending = True
            user_tournament.session_label = None
        
        # Default wants_to_meet to True
        user_tournament.wants_to_meet = True
        
        # Add to database
        db.session.add(user_tournament)
        db.session.commit()
        
        # Log the event
        event_name = 'attend_tournament' if attendance_param == 'attending' else 'maybe_attend_tournament'
        log_event(current_user.id, event_name, {
            'tournament_id': tournament.id,
            'tournament_name': tournament.name,
            'attendance_type': attendance_param
        })

    if request.method == 'POST':
        selected_sessions = request.form.getlist('sessions')
        wants_to_meet = bool(request.form.get('wants_to_meet', False))
        
        if not user_tournament:
            user_tournament = UserTournament(
                user_id=current_user.id,
                tournament_id=tournament.id
            )
            db.session.add(user_tournament)
        
        # Only mark as attending if they selected at least one session
        if selected_sessions:
            user_tournament.attending = True
        else:
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
        
        flash('Your tournament selections have been saved.', 'success')
        
        # Redirect to lanyard page if they're now attending
        if user_tournament.attending:
            return redirect(url_for('user.lanyard'))
        return redirect(url_for('user.my_tournaments'))

    # Import the shared attendance counter function
    from routes.user import get_tournament_attendance_stats
    
    # Get tournament stats using the shared helper function
    # Exclude current user for consistent display across all views
    stats = get_tournament_attendance_stats(tournament.id, include_current_user=False)
    
    # Add lanyards count (not part of standard stats) - only count users with session selections
    other_users_filter = UserTournament.user_id != current_user.id if current_user.is_authenticated else True
    stats['lanyards'] = 0  # Lanyard functionality discontinued
    
    # Use the authenticated template for logged-in users
    attending_count = stats.get('attending', 0) 
    meeting_count = stats.get('meetup', 0)
    
    # Get selected sessions for current user
    selected_sessions = []
    wants_to_meet = True  # Default to True for new users
    user_attending = False
    is_full_attending = False
    
    if user_tournament:
        user_attending = user_tournament.attending
        wants_to_meet = user_tournament.wants_to_meet
        if user_tournament.session_label:
            # Strip spaces from each session to ensure consistent matching
            selected_sessions = [session.strip() for session in user_tournament.session_label.split(',')]
            # User is fully attending if they are attending and have selected sessions
            is_full_attending = user_attending and len(selected_sessions) > 0
    
    # Get session-specific stats using collections.Counter
    # First, get all session labels for users attending this tournament
    user_sessions = (
        db.session.query(UserTournament.session_label)
        .filter_by(tournament_id=tournament.id)
        .filter(UserTournament.attending == True)
        .filter(UserTournament.session_label.isnot(None))
        .all()
    )
    
    # Extract and split all session labels
    all_sessions = []
    for ut in user_sessions:
        if ut.session_label:
            sessions = [session.strip() for session in ut.session_label.split(',') if session.strip()]
            all_sessions.extend(sessions)
    
    # Use Counter to count occurrences of each session
    session_counts = Counter(all_sessions)
    
    # Store in traditional session_stats format for compatibility
    session_stats = {}
    if tournament.sessions:
        for session in tournament.sessions:
            session_stats[session] = {
                'attendees': session_counts.get(session, 0)
            }
    
    # Generate a complete list of days from tournament start to end date
    from datetime import timedelta
    tournament_days = []
    current_date = tournament.start_date
    day_num = 1
    
    # Loop through each day of the tournament
    while current_date <= tournament.end_date:
        tournament_days.append({
            'date': current_date,
            'day_num': day_num,
            'formatted': current_date.strftime('%A, %b %d')
        })
        current_date += timedelta(days=1)
        day_num += 1
    
    # Calculate days until tournament for lanyard reminder
    today = datetime.date.today()
    days_until = (tournament.start_date - today).days if tournament.start_date > today else 0
    
    # Get past tournaments for users attending this tournament
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
    

    
    # Pass session_saved flag to show lanyard button conditionally
    return render_template('user/tournament_detail.html',
                         tournament=tournament,
                         user_tournament=user_tournament,
                         stats=stats,
                         attending_count=attending_count,
                         meeting_count=meeting_count,
                         selected_sessions=selected_sessions,
                         session_stats=session_stats,
                         session_counts=session_counts,  # Pass the Counter object to the template
                         wants_to_meet=wants_to_meet,
                         user_attending=user_attending,
                         is_full_attending=is_full_attending,
                         session_saved=session_saved,
                         days_until=days_until,
                         tournament_days=tournament_days,  # Pass the complete list of tournament days
                         shared_past_tournaments=shared_past_tournaments,  # Pass shared past tournaments
                         sorted_shared_tournaments=sorted_shared_tournaments)  # Pass sorted list for template


@tournaments_bp.route('/tournaments/<tournament_slug>/attend', methods=['POST'])
@login_required
def attend_tournament(tournament_slug):
    tournament = db.session.query(Tournament).filter_by(slug=tournament_slug).first_or_404()
    
    # Make sure the tournament has sessions defined
    if not tournament.sessions or len(tournament.sessions) == 0:
        # Add default sessions - comprehensive set for entire tournament
        tournament.sessions = [
            'Day 1 - Day', 'Day 1 - Night',
            'Day 2 - Day', 'Day 2 - Night',
            'Day 3 - Day', 'Day 3 - Night',
            'Day 4 - Day', 'Day 4 - Night'
        ]
        db.session.flush()  # Save tournament sessions first


    user_tourney = UserTournament.query.filter_by(user_id=current_user.id, tournament_id=tournament.id).first()
    if not user_tourney:
        user_tourney = UserTournament(user_id=current_user.id, tournament_id=tournament.id)
        db.session.add(user_tourney)
    
    # Mark user as attending with placeholder session
    user_tourney.attending = True
    user_tourney.session_label = "placeholder"

    
    # Log the event
    event_data = {
        'tournament_id': tournament.id,
        'tournament_name': tournament.name,
        'attending': True,
        'session_preselected': False
    }
    log_event(current_user.id, 'attend_tournament', event_data)
    
    db.session.commit()
    
    flash('Please select which sessions you\'ll attend.', 'info')
    return redirect(url_for('user.tournament_detail', slug=tournament_slug))


@tournaments_bp.route('/tournaments/<tournament_slug>/unattend', methods=['POST'])
@login_required
def unattend_tournament(tournament_slug):
    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
    
    # Log the event before deleting
    event_data = {
        'tournament_id': tournament.id,
        'tournament_name': tournament.name
    }
    log_event(current_user.id, 'unattend_tournament', event_data)
    
    # Update the user tournament to "not attending" state
    user_tournament = UserTournament.query.filter_by(user_id=current_user.id, tournament_id=tournament.id).first()
    if user_tournament:
        user_tournament.attending = False
        user_tournament.session_label = ""
        user_tournament.attendance_type = None
        user_tournament.wants_to_meet = False
    
    db.session.commit()
    
    return redirect(url_for('user.tournament_detail', slug=tournament_slug))


@tournaments_bp.route('/tournaments/<tournament_slug>/update', methods=['POST'])
@login_required
def update_sessions(tournament_slug):
    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()

    selected_sessions = request.form.getlist("sessions")
    wants_to_meet = bool(request.form.get("wants_to_meet"))

    # Track previous state for event logging
    is_new_registration = False
    previous_sessions = None
    previous_wants_to_meet = None
    previous_attending = None

    # update UserTournament entry
    user_tourney = db.session.query(UserTournament).filter_by(user_id=current_user.id, tournament_id=tournament.id).first()
    if not user_tourney:
        user_tourney = UserTournament(user_id=current_user.id, tournament_id=tournament.id)
        db.session.add(user_tourney)
        is_new_registration = True
    else:
        previous_sessions = user_tourney.session_label
        previous_wants_to_meet = user_tourney.wants_to_meet
        previous_attending = user_tourney.attending

    # Format sessions consistently with a comma separator
    user_tourney.session_label = ", ".join(selected_sessions) if selected_sessions else None
    user_tourney.wants_to_meet = wants_to_meet

    # Only mark as attending if they selected at least one session
    if selected_sessions:
        user_tourney.attending = True
    else:
        user_tourney.attending = False

    db.session.commit()

    # Log the event
    event_data = {
        'tournament_id': tournament.id,
        'tournament_name': tournament.name,
        'selected_sessions': selected_sessions,
        'wants_to_meet': wants_to_meet,
        'is_new_registration': is_new_registration,
        'previous_sessions': previous_sessions,
        'previous_wants_to_meet': previous_wants_to_meet,
        'previous_attending': previous_attending,
        'now_attending': user_tourney.attending
    }
    log_event(current_user.id, 'tournament_session_update', event_data)

    # Flash message to inform user of changes
    if user_tourney.attending:
        flash('Your tournament session selections have been saved.', 'success')
    else:
        flash('Your selections were saved, but you will not be marked as attending until you select at least one session.', 'warning')

    return redirect(url_for('user.tournament_detail', slug=tournament_slug))

@tournaments_bp.route("/tournaments/<tournament_slug>/save_sessions", methods=['POST'])
@login_required
def save_sessions(tournament_slug):
    """Save selected sessions for a tournament"""
    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
    
    # Get selected sessions and wants_to_meet preference
    selected_sessions = request.form.getlist('sessions')
    # Standard checkbox handling - it's present in the form data only when checked
    wants_to_meet = 'wants_to_meet' in request.form
    
    # Get or create user tournament registration
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id, 
        tournament_id=tournament.id
    ).first()
    
    is_new = False
    previous_sessions = None
    previous_wants_to_meet = None
    previous_attending = None
    
    if not user_tournament:
        # Create a new UserTournament record
        user_tournament = UserTournament()
        user_tournament.user_id = current_user.id
        user_tournament.tournament_id = tournament.id
        db.session.add(user_tournament)
        is_new = True
    else:
        previous_sessions = user_tournament.session_label
        previous_wants_to_meet = user_tournament.wants_to_meet
        previous_attending = user_tournament.attending
    
    # Always mark as attending when saving sessions, even if none selected
    # This ensures the user's attendance status is preserved
    user_tournament.attending = True
    
    # Also explicitly mark the attendance_type as 'attending'
    # This is critical for proper display on My Tournaments page
    user_tournament.attendance_type = 'attending'
    
    # Make sure we don't lose the attendance_type value
    # If a user is "maybe" attending, preserve that setting when saving sessions
    if not user_tournament.attendance_type or user_tournament.attendance_type == '':
        user_tournament.attendance_type = 'attending'  # Default to attending if not set
    
    # Log the session selection count
    if selected_sessions:
        pass
    else:
        pass
    
    user_tournament.wants_to_meet = wants_to_meet
    
    # Store sessions with consistent comma-only formatting to avoid matching issues
    # The comma-separated format without extra spaces ensures proper highlighting
    # When a checkbox is unchecked, it won't be in the form data, so this correctly handles removals
    # First, get all possible sessions for this tournament
    all_tournament_sessions = []
    if hasattr(tournament, 'sessions') and tournament.sessions:
        # The sessions data structure depends on how it was defined
        # If it's already a list of day/night sessions, use it directly
        if isinstance(tournament.sessions, list) and all(isinstance(s, str) for s in tournament.sessions):
            all_tournament_sessions = tournament.sessions
        # Otherwise, if it's a list of day objects with day_num
        else:
            try:
                days = tournament.sessions
                for day in days:
                    if isinstance(day, dict) and 'day_num' in day:
                        day_key = f"Day {day['day_num']} - Day"
                        night_key = f"Day {day['day_num']} - Night"
                        all_tournament_sessions.append(day_key)
                        all_tournament_sessions.append(night_key)
            except Exception as e:

                # Fallback - use basic days 1-7 if we can't process the sessions
                for i in range(1, 8):
                    all_tournament_sessions.append(f"Day {i} - Day")
                    all_tournament_sessions.append(f"Day {i} - Night")


    
    # Store a clean comma-separated list of selected sessions
    # COMPLETE REWRITE OF SESSION HANDLING:
    # 1. We will explicitly REPLACE the entire session_label with only what's currently selected
    # 2. Unselected sessions will not be included at all - this ensures proper clearing
    
    # COMPLETE REBUILD OF SESSION SELECTION LOGIC:
    
    # 1. First, extract all sessions that were previously selected
    old_sessions = []
    if user_tournament.session_label:
        old_sessions = [s.strip() for s in user_tournament.session_label.split(',') if s.strip()]
    
    # 2. For debugging, log what we had before

    
    # 3. Convert current selections to a clean list with no duplicates
    unique_sessions = list(set(selected_sessions)) if selected_sessions else []
    
    # 4. More detailed logging showing comparison

    
    # 5. Completely replace the old session_label with only what's currently checked
    user_tournament.session_label = ','.join(unique_sessions) if unique_sessions else ''
    
    # 6. Verify final result after save

    

    
    # Log the event for tracking
    event_data = {
        'tournament_id': tournament.id,
        'tournament_name': tournament.name,
        'selected_sessions': selected_sessions,
        'wants_to_meet': wants_to_meet,
        'is_new': is_new,
        'previous_sessions': previous_sessions,
        'previous_wants_to_meet': previous_wants_to_meet,
        'previous_attending': previous_attending,
        'attending': user_tournament.attending,
        'attendance_type': user_tournament.attendance_type
    }
    log_event(current_user.id, 'tournament_session_update', event_data)
    
    db.session.commit()
    
    if selected_sessions:
        flash('Your tournament sessions have been saved.', 'success')
    else:
        flash('Your tournament preferences have been saved.', 'success')
    
    # Redirect to My Tournaments page after saving sessions
    # This ensures users see their tournaments and lanyard reminder (if eligible)
    return redirect(url_for('user.my_tournaments'))

@tournaments_bp.route("/tournaments/<tournament_slug>/attend/new", methods=['POST'])
@login_required
def attend_tournament_new(tournament_slug):
    """Handle new attendance type for Maybe Attending vs I'm Attending"""
    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
    attendance_type = request.form.get('attendance_type', 'attending')  # Default to full attending

    # Create or update user tournament registration
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament.id
    ).first()

    if not user_tournament:
        user_tournament = UserTournament(
            user_id=current_user.id,
            tournament_id=tournament.id
        )
        db.session.add(user_tournament)
    
    # Set attendance based on type - maybe = not attending but has placeholder
    if attendance_type == 'maybe':
        user_tournament.attending = False
        user_tournament.session_label = "placeholder"
        flash('You are marked as "Maybe Attending" this tournament. You can still select specific sessions.', 'success')
    else:
        # For full attending
        user_tournament.attending = True
        user_tournament.session_label = "placeholder"
        flash('Please select which sessions you\'ll attend.', 'info')
    
    # Set the attendance_type field
    user_tournament.attendance_type = attendance_type
    
    # Log the event
    event_data = {
        'tournament_id': tournament.id,
        'tournament_name': tournament.name,
        'attendance_type': attendance_type,
        'attending': user_tournament.attending
    }
    log_event(current_user.id, 'attend_tournament', event_data)

    db.session.commit()
    
    # Redirect to tournament detail page with the appropriate attendance type
    return redirect(url_for('user.tournament_detail', slug=tournament_slug))

@tournaments_bp.route("/tournaments/<tournament_slug>/attending", methods=['POST'])
@login_required
def mark_attending(tournament_slug):
    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()

    # Create or update user tournament registration
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament.id
    ).first()

    # Get selected sessions from the form
    selected_sessions = request.form.getlist('sessions')
    wants_to_meet = bool(request.form.get('wants_to_meet', False))

    if not user_tournament:
        user_tournament = UserTournament(
            user_id=current_user.id,
            tournament_id=tournament.id
        )
        db.session.add(user_tournament)
    
    # Update session selections
    user_tournament.session_label = ','.join(selected_sessions) if selected_sessions else None
    user_tournament.wants_to_meet = wants_to_meet
    
    # Always mark as attending (either maybe or full attending)
    user_tournament.attending = True
    
    # Update attendance_type based on session selections
    if selected_sessions:
        user_tournament.attendance_type = 'attending'
        flash('You are now registered as attending this tournament.', 'success')
    else:
        # If they didn't select any sessions, mark as "maybe"
        user_tournament.attendance_type = 'maybe'
        flash('Your preferences have been saved. You can select sessions later.', 'success')

    # Log the event
    event_data = {
        'tournament_id': tournament.id,
        'tournament_name': tournament.name,
        'selected_sessions': selected_sessions,
        'wants_to_meet': wants_to_meet,
        'attending': user_tournament.attending
    }
    log_event(current_user.id, 'tournament_attendance_update', event_data)

    db.session.commit()

    # Redirect back with session_saved parameter for lanyard button display when there are sessions
    if selected_sessions:
        return redirect(url_for('user.tournament_detail', slug=tournament_slug, session_saved=1))
    else:
        return redirect(url_for('user.tournament_detail', slug=tournament_slug))

@tournaments_bp.route("/tournaments/public/<slug>")
def public_tournament_page(slug):
    try:
        tournament = Tournament.query.filter_by(slug=slug).first_or_404()
        attending_count = UserTournament.query.filter_by(tournament_id=tournament.id, attending=True).count()
        return render_template("public_tournament.html", tournament=tournament, attending_count=attending_count)
    except Exception as e:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.public_home'))