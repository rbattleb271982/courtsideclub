import datetime
import json
try:
    from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
    from flask_login import login_required, current_user
except ImportError:
    pass  # Imports will be available at runtime

from models import db, User, Tournament, UserTournament
from sqlalchemy import and_, or_

# Initialize blueprint
tournaments_bp = Blueprint('tournaments', __name__)

@tournaments_bp.route('/')
def index():
    return redirect(url_for('tournaments.list_tournaments'))

@tournaments_bp.route('/tournaments')
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

    # Get today's date for highlighting current tournaments
    today = datetime.datetime.now().date()

    # Calculate attendance and meetup counts for each tournament
    attendance_counts = {}
    for tournament in tournaments:
        # Count users who have registered for this tournament
        attending_users = UserTournament.query.filter_by(
            tournament_id=tournament.id
        ).count()

        # Count users who are open to meeting
        meeting_users = UserTournament.query.filter_by(
            tournament_id=tournament.id,
            open_to_meet=True
        ).count()

        attendance_counts[tournament.id] = {
            'attending': attending_users,
            'meeting': meeting_users
        }

    return render_template('tournaments.html', 
                          tournaments=tournaments,
                          all_tournaments=all_tournaments,
                          today=today,
                          name_filter=name_filter,
                          country_filter=country_filter,
                          attendance_counts=attendance_counts)

@tournaments_bp.route('/tournaments/<tournament_id>')
@login_required
def tournament_detail(tournament_id):
    # Find the tournament
    tournament = Tournament.query.get(tournament_id)

    if not tournament:
        flash('Tournament not found.', 'danger')
        return redirect(url_for('tournaments.list_tournaments'))

    # Get users who are open to meeting for this tournament
    raised_hands = []
    user_tournaments = UserTournament.query.filter_by(
        tournament_id=tournament_id,
        open_to_meet=True
    ).all()

    for user_tournament in user_tournaments:
        user = user_tournament.user
        for day in user_tournament.dates:
            sessions_str = ", ".join(user_tournament.sessions)
            raised_hands.append({
                'name': user.get_full_name(),
                'email': user.email,
                'day': day,
                'sessions': sessions_str,
                'user_id': user.id
            })

    # Calculate overall attendance count (excluding current user unless they've saved sessions AND are marked as attending)
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament_id
    ).first()

    # Get only users who are marked as attending
    attending_count = UserTournament.query.filter(
        UserTournament.tournament_id == tournament_id,
        UserTournament.user_id != current_user.id,
        UserTournament.attending == True
    ).count()

    # Add current user to count only if they have saved sessions AND are marked as attending
    if user_tournament and user_tournament.attending:
        attending_count += 1

    # Calculate meeting count (excluding current user unless they've saved sessions AND are marked as attending)
    meeting_count = UserTournament.query.filter(
        UserTournament.tournament_id == tournament_id,
        UserTournament.open_to_meet == True,
        UserTournament.user_id != current_user.id,
        UserTournament.attending == True
    ).count()

    # Add current user to meeting count only if they have saved sessions, are marked as attending, and are open to meeting
    if user_tournament and user_tournament.attending and user_tournament.open_to_meet:
        meeting_count += 1

    # For backward compatibility during migration
    # Check if current user has a UserTournament record or is in the legacy fields
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament_id
    ).first()

    user_attending = user_tournament is not None or tournament_id in current_user.attending
    user_raised_hand = (user_tournament and user_tournament.open_to_meet) or tournament_id in current_user.raised_hand

    # Parse tournament sessions into days for the template and calculate calendar dates
    from datetime import timedelta

    days = {}
    day_dates = {}  # Maps day names to actual calendar dates

    for session_str in tournament.sessions:
        parts = session_str.split(' - ')
        day = parts[0]
        session_type = parts[1]

        if day not in days:
            days[day] = []

            # Extract day number and calculate calendar date
            day_number = int(day.split(' ')[1])  # e.g., "Day 1" -> 1
            calendar_date = tournament.start_date + timedelta(days=day_number - 1)
            day_dates[day] = calendar_date

        if session_type not in days[day]:
            days[day].append(session_type)

    # Calculate per-day and per-session attendance counts
    day_attendance = {}
    for day_name in days.keys():
        day_attendance[day_name] = {
            'attending': 0,
            'meeting': 0,
            'sessions': {}
        }
        # Initialize sessions
        for session in days[day_name]:
            day_attendance[day_name]['sessions'][session] = {
                'attending': 0,
                'meeting': 0
            }

    # Fetch all users with their attendance details for this tournament
    # Only count users marked as attending=True
    user_tournaments = UserTournament.query.filter_by(
        tournament_id=tournament_id,
        attending=True
    ).all()

    # Count attendance per day and session using the user_tournaments
    for user_tournament in user_tournaments:
        # Skip current user unless they have saved sessions and are marked as attending
        if user_tournament.user_id == current_user.id and not user_tournament.attending:
            continue

        for day in user_tournament.dates:
            if day in day_attendance:
                # Increment day counter
                day_attendance[day]['attending'] += 1
                if user_tournament.open_to_meet:
                    day_attendance[day]['meeting'] += 1

                # Increment session counters
                for session in user_tournament.sessions:
                    if session in day_attendance[day]['sessions']:
                        day_attendance[day]['sessions'][session]['attending'] += 1
                        if user_tournament.open_to_meet:
                            day_attendance[day]['sessions'][session]['meeting'] += 1

    return render_template('tournament_detail.html',
                          tournament=tournament,
                          user_attending=user_attending,
                          user_raised_hand=user_raised_hand,
                          raised_hands=raised_hands,
                          attending_count=attending_count,
                          meeting_count=meeting_count,
                          days=days,
                          day_dates=day_dates,
                          day_attendance=day_attendance)

@tournaments_bp.route('/tournaments/<tournament_id>/attend', methods=['POST'])
@login_required
def attend_tournament(tournament_id):
    # Validate tournament exists
    tournament = Tournament.query.get(tournament_id)

    if not tournament:
        flash('Tournament not found.', 'danger')
        return redirect(url_for('tournaments.list_tournaments'))

    # Get current user
    user = User.query.get(current_user.id)

    # Check if this is a removal request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    remove = request.form.get('remove') == 'true'

    # Check if user has existing registration for this tournament
    user_tournament = UserTournament.query.filter_by(
        user_id=user.id,
        tournament_id=tournament_id
    ).first()

    if remove:
        # Set attending=False instead of deleting the record
        if user_tournament:
            user_tournament.attending = False
            user_tournament.sessions = []
            db.session.commit()

            message = f"You're no longer attending {tournament.name}."
            if is_ajax:
                return jsonify({'success': True, 'message': message})
            else:
                flash(message, 'info')
                # Redirect to home instead of tournament list when canceling attendance
                return redirect(url_for('user.home'))
    else:
        # Handle simple "I'm attending" checkbox from tournaments list
        attending_checkbox = request.form.get('attending') == 'true'

        if attending_checkbox:
            # Create a UserTournament if it doesn't exist
            if not user_tournament:
                user_tournament = UserTournament(
                    user_id=user.id,
                    tournament_id=tournament_id,
                    dates=[],
                    sessions=[],
                    open_to_meet=True
                )
                db.session.add(user_tournament)
                db.session.commit()

            return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))

        # Handle session selections and meeting preferences from the session form
        elif 'sessions' in request.form:
            selected_days = []
            selected_sessions = []

            # Process the session form data to extract days and sessions
            for field_name, value in request.form.items():
                if field_name.startswith('sessions['):
                    # Extract the day key from the field name
                    # Format: sessions[Day X][Day|Night]
                    parts = field_name.split('[')
                    if len(parts) >= 3:
                        day_key = parts[1].rstrip(']')
                        session_type = parts[2].rstrip(']')

                        # Check if the checkbox is checked
                        if value == 'on':
                            if day_key not in selected_days:
                                selected_days.append(day_key)
                            if session_type not in selected_sessions:
                                selected_sessions.append(session_type)

            # Check for meeting preference in the same form
            meeting_preference = request.form.get('meeting_preference', 'Yes')  # Default to 'Yes'
            open_to_meet = meeting_preference == 'Yes'

            # If days and sessions were selected, update or create UserTournament
            if selected_days and selected_sessions:
                if user_tournament:
                    # Update existing registration
                    user_tournament.dates = selected_days
                    user_tournament.sessions = selected_sessions
                    user_tournament.open_to_meet = open_to_meet
                    user_tournament.attending = True
                else:
                    # Create new registration
                    user_tournament = UserTournament(
                        user_id=user.id,
                        tournament_id=tournament_id,
                        dates=selected_days,
                        sessions=selected_sessions,
                        open_to_meet=open_to_meet,
                        attending=True
                    )
                    db.session.add(user_tournament)

                message = f"Your selections for {tournament.name} have been saved!"
            else:
                # No sessions were selected - set attending to false
                if user_tournament:
                    user_tournament.attending = False
                    user_tournament.sessions = []
                message = f"Please select at least one session to confirm your attendance at {tournament.name}."

            # Save changes and respond
            db.session.commit()

            if is_ajax:
                return jsonify({'success': True, 'message': message})
            else:
                flash(message, 'success')
                # Redirect to home page after saving, not back to tournament detail
                return redirect(url_for('user.home'))
        else:
            # Default behavior - create registration but don't mark as attending until sessions are selected
            if not user_tournament:
                user_tournament = UserTournament(
                    user_id=user.id,
                    tournament_id=tournament_id,
                    dates=[],
                    sessions=[],
                    open_to_meet=True,
                    attending=False
                )
                db.session.add(user_tournament)
                db.session.commit()

            if is_ajax:
                return jsonify({'success': True})
            else:
                return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))

    # This is reached only in the default case (not is_ajax and not remove)
    return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))

@tournaments_bp.route('/tournaments/past', methods=['GET', 'POST'])
@login_required
def past_tournaments():
    # Get all tournaments for the list, sorted alphabetically by name
    all_tournaments = Tournament.query.order_by(Tournament.name).all()

    # Get the user's past tournaments list
    user = User.query.get(current_user.id)

    # Combine both legacy and new past tournaments data
    past_tournaments_legacy = list(user.past_tournaments_json) if hasattr(user, 'past_tournaments_json') and user.past_tournaments_json else []
    attended_tournaments_ids = [t.id for t in user.attended_tournaments]
    past_tournaments = list(set(past_tournaments_legacy + attended_tournaments_ids))

    # Handle form submission
    if request.method == 'POST':
        # Reset the attended_tournaments relationship
        user.attended_tournaments = []

        # Process checked tournaments
        selected_tournaments = []
        for field_name, value in request.form.items():
            if field_name.startswith('tournament_'):
                # Extract tournament_id from field name (format: tournament_<id>)
                tournament_id = field_name.split('_', 1)[1]

                # Add to the list if checked
                if value == 'on':
                    tournament = Tournament.query.get(tournament_id)
                    if tournament:
                        selected_tournaments.append(tournament)

        # Update user's attended_tournaments relationship
        user.attended_tournaments = selected_tournaments

        # For backward compatibility
        user.past_tournaments_json = [t.id for t in selected_tournaments]

        db.session.commit()

        flash("Your past tournament selections have been saved.", 'success')
        return redirect(url_for('user.home'))

    return render_template('past_tournaments.html', 
                          all_tournaments=all_tournaments,
                          past_tournaments=past_tournaments)

@tournaments_bp.route('/tournaments/<tournament_id>/raise_hand', methods=['POST'])
@login_required
def raise_hand(tournament_id):
    # Get form data - simplified to just "Yes" or "No" for meeting preference
    meeting_pref = request.form.get('meeting_preference')

    # Validate tournament exists
    tournament = Tournament.query.get(tournament_id)

    if not tournament:
        flash('Tournament not found.', 'danger')
        return redirect(url_for('tournaments.list_tournaments'))

    # Check if the user has a registration for this tournament
    user = User.query.get(current_user.id)
    user_tournament = UserTournament.query.filter_by(
        user_id=user.id,
        tournament_id=tournament_id
    ).first()

    if not user_tournament:
        flash("You need to mark yourself as attending this tournament before setting meeting preferences.", 'warning')
        return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))

    # Update open_to_meet flag based on meeting preference
    if meeting_pref == 'Yes':
        user_tournament.open_to_meet = True
        flash("You're now visible as open to meeting other fans at this tournament!", 'success')
    else:
        user_tournament.open_to_meet = False
        if meeting_pref == 'No':
            flash("You're marked as not open to meeting at this tournament.", 'info')
        else:
            flash("Your meeting preference has been reset.", 'info')

    db.session.commit()

    # Redirect to home instead of tournament detail after updating meeting preferences
    return redirect(url_for('user.home'))


@tournaments_bp.route("/tournaments")
def public_tournaments_page():
    tournaments = Tournament.query.order_by(Tournament.start_date).all()
    return render_template("tournaments_landing.html", tournaments=tournaments)

@tournaments_bp.route("/tournaments/<slug>")
def public_tournament_page(slug):
    tournament = Tournament.query.filter_by(slug=slug).first_or_404()
    attending_count = UserTournament.query.filter_by(tournament_id=tournament.id, attending=True).count()
    return render_template("public_tournament.html", tournament=tournament, attending_count=attending_count)