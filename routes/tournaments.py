from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Tournament, UserTournament, User, past_tournaments
import datetime
from services.event_logger import log_event

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


@tournaments_bp.route('/tournaments/<tournament_slug>', methods=['GET', 'POST'])
@login_required
def view_tournament(tournament_slug):
    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
    
    # Get current user's tournament registration
    user_tournament = UserTournament.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament.id
    ).first()

    if request.method == 'POST':
        attending = request.form.get('attending') == 'true'
        selected_sessions = request.form.getlist('sessions')
        
        if not user_tournament:
            user_tournament = UserTournament(
                user_id=current_user.id,
                tournament_id=tournament.id
            )
            db.session.add(user_tournament)
        
        user_tournament.attending = attending
        user_tournament.session_label = ','.join(selected_sessions) if selected_sessions else None
        
        db.session.commit()
        
        if attending and selected_sessions:
            return redirect(url_for('user.lanyard'))
        return redirect(url_for('user.my_tournaments'))

    # Get tournament stats
    stats = {
        'attending': UserTournament.query.filter_by(tournament_id=tournament.id, attending=True).count(),
        'meetup': UserTournament.query.filter_by(tournament_id=tournament.id, attending=True, wants_to_meet=True).count(),
        'lanyards': UserTournament.query.filter_by(tournament_id=tournament.id, attending=True).join(User).filter_by(lanyard_ordered=True).count()
    }

    return render_template('public/tournament_detail.html',
                         tournament=tournament,
                         user_tournament=user_tournament,
                         stats=stats)


@tournaments_bp.route('/tournaments/<tournament_slug>/attend', methods=['POST'])
@login_required
def attend_tournament_new(tournament_slug):
    tournament = db.session.query(Tournament).filter_by(slug=tournament_slug).first_or_404()

    user_tourney = UserTournament.query.filter_by(user_id=current_user.id, tournament_id=tournament.id).first()
    if not user_tourney:
        user_tourney = UserTournament(user_id=current_user.id, tournament_id=tournament.id)
        db.session.add(user_tourney)

    db.session.commit()
    return redirect(url_for('tournaments.view_tournament', tournament_slug=tournament_slug))


@tournaments_bp.route('/tournaments/<tournament_slug>/unattend', methods=['POST'])
@login_required
def unattend_tournament(tournament_slug):
    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
    UserTournament.query.filter_by(user_id=current_user.id, tournament_id=tournament.id).delete()
    db.session.commit()
    return redirect(url_for('tournaments.view_tournament', tournament_slug=tournament_slug))


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

@tournaments_bp.route("/tournaments/<tournament_slug>/attending", methods=['POST'])
@login_required
def mark_attending(tournament_slug):
    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()

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

    return redirect(url_for('tournaments.view_tournament', tournament_slug=tournament_slug))

@tournaments_bp.route("/tournaments/public/<slug>")
def public_tournament_page(slug):
    try:
        tournament = Tournament.query.filter_by(slug=slug).first_or_404()
        attending_count = UserTournament.query.filter_by(tournament_id=tournament.id, attending=True).count()
        return render_template("public_tournament.html", tournament=tournament, attending_count=attending_count)
    except Exception as e:
        flash('Tournament not found', 'error')
        return redirect(url_for('main.public_home'))