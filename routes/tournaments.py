from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Tournament, UserTournament, User, past_tournaments
import datetime

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

    # Add stats to each tournament
    for tournament in tournaments:
        # Count users who are attending
        tournament.attendee_count = UserTournament.query.filter_by(
            tournament_id=tournament.id,
            attending=True
        ).count()

        # Count users who are open to meeting
        tournament.hand_raised_count = UserTournament.query.filter_by(
            tournament_id=tournament.id,
            attending=True,
            open_to_meet=True
        ).count()

        # Count users who ordered lanyards
        tournament.lanyard_count = UserTournament.query.filter_by(
            tournament_id=tournament.id,
            attending=True
        ).join(User).filter_by(lanyard_ordered=True).count()

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


@tournaments_bp.route('/tournaments/<tournament_slug>')
def view_tournament(tournament_slug):
    tournament = db.session.query(Tournament).filter_by(id=tournament_slug).first()
    if not tournament:
        return "Tournament not found", 404

    user_attending = False
    selected_sessions = []
    wants_to_meet = False

    if current_user.is_authenticated:
        user_tourney = db.session.query(UserTournament).filter_by(user_id=current_user.id, tournament_id=tournament.id).first()
        if user_tourney:
            user_attending = True
            selected_sessions = user_tourney.session_label.split(", ") if user_tourney.session_label else []
            wants_to_meet = user_tourney.wants_to_meet

    return render_template("tournament_detail.html", tournament=tournament,
                           user_attending=user_attending,
                           selected_sessions=selected_sessions,
                           wants_to_meet=wants_to_meet)


@tournaments_bp.route('/tournaments/<tournament_slug>/attend', methods=['POST'])
@login_required
def attend_tournament_new(tournament_slug):
    tournament = db.session.query(Tournament).filter_by(id=tournament_slug).first()
    if not tournament:
        return "Tournament not found", 404

    user_tourney = UserTournament.query.filter_by(user_id=current_user.id, tournament_id=tournament.id).first()
    if not user_tourney:
        user_tourney = UserTournament(user_id=current_user.id, tournament_id=tournament.id)
        db.session.add(user_tourney)

    db.session.commit()
    return redirect(url_for('tournaments.view_tournament', tournament_slug=tournament_slug))


@tournaments_bp.route('/tournaments/<tournament_slug>/unattend', methods=['POST'])
@login_required
def unattend_tournament(tournament_slug):
    UserTournament.query.filter_by(user_id=current_user.id, tournament_id=tournament_slug).delete()
    db.session.commit()
    return redirect(url_for('tournaments.view_tournament', tournament_slug=tournament_slug))


@tournaments_bp.route('/tournaments/<tournament_slug>/update', methods=['POST'])
@login_required
def update_sessions(tournament_slug):
    tournament = db.session.query(Tournament).filter_by(id=tournament_slug).first()
    if not tournament:
        return "Tournament not found", 404

    selected_sessions = request.form.getlist("sessions")
    wants_to_meet = bool(request.form.get("wants_to_meet"))

    # Track previous state for event logging
    is_new_registration = False
    previous_sessions = None
    previous_wants_to_meet = None

    # update UserTournament entry
    user_tourney = db.session.query(UserTournament).filter_by(user_id=current_user.id, tournament_id=tournament.id).first()
    if not user_tourney:
        user_tourney = UserTournament(user_id=current_user.id, tournament_id=tournament.id)
        db.session.add(user_tourney)
        is_new_registration = True
    else:
        previous_sessions = user_tourney.session_label
        previous_wants_to_meet = user_tourney.wants_to_meet

    user_tourney.session_label = ", ".join(selected_sessions)
    user_tourney.wants_to_meet = wants_to_meet

    # If session is selected, mark as attending
    if selected_sessions:
        user_tourney.attending = True

    db.session.commit()

    # Log the event
    from services.event_logger import log_event
    event_data = {
        'tournament_id': tournament.id,
        'tournament_name': tournament.name,
        'selected_sessions': selected_sessions,
        'wants_to_meet': wants_to_meet,
        'is_new_registration': is_new_registration,
        'previous_sessions': previous_sessions,
        'previous_wants_to_meet': previous_wants_to_meet
    }
    log_event(current_user.id, 'tournament_session_update', event_data)

    return redirect(url_for('tournaments.view_tournament', tournament_slug=tournament_slug))

@tournaments_bp.route("/tournaments/<slug>/attending", methods=['POST'])
@login_required
def mark_attending(slug):
    tournament = Tournament.query.filter_by(slug=slug).first_or_404()

    # Create or update user tournament registration
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament.id
    ).first()

    if not user_tournament:
        user_tournament = UserTournament(
            user_id=current_user.id,
            tournament_id=tournament.id,
            attending=True
        )
        db.session.add(user_tournament)
    else:
        user_tournament.attending = True

    db.session.commit()

    return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament.id))

@tournaments_bp.route("/tournaments/<slug>")
def public_tournament_page(slug):
    try:
        tournament = Tournament.query.filter_by(slug=slug).first_or_404()
        attending_count = UserTournament.query.filter_by(tournament_id=tournament.id, attending=True).count()
        return render_template("public_tournament.html", tournament=tournament, attending_count=attending_count)
    except Exception as e:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.homepage'))

import datetime
import json
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Tournament, UserTournament
from sqlalchemy import and_, or_

# Root route removed to allow main blueprint's homepage to work
# @tournaments_bp.route('/')
# def index():
#     return redirect(url_for('tournaments.list_tournaments'))



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
        open_to_meet=True,
        attending=True  # Only include users who are actually attending
    ).all()

    for user_tournament in user_tournaments:
        user = user_tournament.user
        # Use session_label directly or extract day/session from it
        if user_tournament.session_label:
            raised_hands.append({
                'name': user.get_full_name(),
                'email': user.email,
                'session': user_tournament.session_label,
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

    # Get the current user's tournament registration
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament_id
    ).first()

    # Check if user is attending and open to meeting
    user_attending = user_tournament is not None and user_tournament.attending
    user_open_to_meet = user_tournament is not None and user_tournament.open_to_meet

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
                          user_open_to_meet=user_open_to_meet,
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
                    session_label=None,
                    open_to_meet=True,
                    wants_to_meet=True
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
                # Create a meaningful session label from the selected days and sessions
                session_label = ""
                if selected_days and selected_sessions:
                    day_str = ", ".join(selected_days)
                    session_str = ", ".join(selected_sessions)
                    session_label = f"Days: {day_str} | Sessions: {session_str}"

                if user_tournament:
                    # Update existing registration
                    user_tournament.session_label = session_label
                    user_tournament.open_to_meet = open_to_meet
                    user_tournament.attending = True
                else:
                    # Create new registration

                    user_tournament = UserTournament(
                        user_id=user.id,
                        tournament_id=tournament_id,
                        session_label=session_label,
                        open_to_meet=open_to_meet,
                        wants_to_meet=open_to_meet,
                        attending=True
                    )
                    db.session.add(user_tournament)

                message = f"Your selections for {tournament.name} have been saved!"
            else:
                # No sessions were selected - set attending to false
                if user_tournament:
                    user_tournament.attending = False
                    user_tournament.session_label = None
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

    # Get the user's past tournaments from the many-to-many relationship
    user = User.query.get(current_user.id)

    # Get past tournament IDs from the past_tournaments table
    past_tournaments_query = db.session.query(past_tournaments.c.tournament_id).filter(
        past_tournaments.c.user_id == user.id
    ).all()
    past_tournaments = [t[0] for t in past_tournaments_query]

    # Handle form submission
    if request.method == 'POST':
        # First, delete all current past tournament entries for this user
        db.session.execute(
            db.delete(past_tournaments).where(past_tournaments.c.user_id == user.id)
        )

        # Process checked tournaments
        selected_tournament_ids = []
        for field_name, value in request.form.items():
            if field_name.startswith('tournament_'):
                # Extract tournament_id from field name (format: tournament_<id>)
                tournament_id = field_name.split('_', 1)[1]

                # Add to the list if checked
                if value == 'on':
                    selected_tournament_ids.append(tournament_id)

        # Add new entries to past_tournaments table
        for tournament_id in selected_tournament_ids:
            db.session.execute(
                db.insert(past_tournaments).values(
                    user_id=user.id,
                    tournament_id=tournament_id
                )
            )

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