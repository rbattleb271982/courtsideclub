from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, User, Tournament
import datetime
import json

# Initialize blueprint
tournaments_bp = Blueprint('tournaments', __name__)

@tournaments_bp.route('/')
def index():
    return redirect(url_for('tournaments.list_tournaments'))

@tournaments_bp.route('/tournaments')
@login_required
def list_tournaments():
    # Get all tournaments
    query = Tournament.query
    
    # Filter by date if requested
    date_filter = request.args.get('date')
    if date_filter:
        try:
            filter_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(Tournament.start_date <= filter_date, 
                                Tournament.end_date >= filter_date)
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'warning')
    
    # Get the tournaments
    tournaments = query.all()
    
    # Get today's date for highlighting current tournaments
    today = datetime.datetime.now().date()
    
    return render_template('tournaments.html', 
                          tournaments=tournaments, 
                          today=today,
                          date_filter=date_filter)

@tournaments_bp.route('/tournaments/<tournament_id>')
@login_required
def tournament_detail(tournament_id):
    # Find the tournament
    tournament = Tournament.query.get(tournament_id)
    
    if not tournament:
        flash('Tournament not found.', 'danger')
        return redirect(url_for('tournaments.list_tournaments'))
    
    # Get users who raised hands for this tournament
    raised_hands = []
    users_with_raised_hands = User.query.filter(
        User.raised_hand.contains({tournament_id: {'day': lambda d: True}})
    ).all()
    
    for user in users_with_raised_hands:
        if tournament_id in user.raised_hand:
            raised_hands.append({
                'name': user.get_full_name(),
                'email': user.email,
                'day': user.raised_hand[tournament_id].get('day'),
                'session': user.raised_hand[tournament_id].get('session')
            })
    
    # Check if current user is attending
    user_attending = tournament_id in current_user.attending
    
    # Check if current user has raised hand
    user_raised_hand = tournament_id in current_user.raised_hand
    if user_raised_hand:
        user_raised_day = current_user.raised_hand[tournament_id].get('day')
        user_raised_session = current_user.raised_hand[tournament_id].get('session')
    else:
        user_raised_day = None
        user_raised_session = None
    
    return render_template('tournament_detail.html',
                          tournament=tournament,
                          user_attending=user_attending,
                          user_raised_hand=user_raised_hand,
                          user_raised_day=user_raised_day,
                          user_raised_session=user_raised_session,
                          raised_hands=raised_hands)

@tournaments_bp.route('/tournaments/<tournament_id>/attend', methods=['POST'])
@login_required
def attend_tournament(tournament_id):
    # Validate tournament exists
    tournament = Tournament.query.get(tournament_id)
    
    if not tournament:
        flash('Tournament not found.', 'danger')
        return redirect(url_for('tournaments.list_tournaments'))
    
    # Update user's attending information
    user = User.query.get(current_user.id)
    attending = dict(user.attending) if user.attending else {}
    
    # Check if this is a removal request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    remove = request.form.get('remove') == 'true'
    
    if remove:
        if tournament_id in attending:
            del attending[tournament_id]
            message = f"You're no longer attending {tournament.name}."
            if is_ajax:
                return jsonify({'success': True, 'message': message})
            else:
                flash(message, 'info')
    else:
        # Get session information
        day = request.form.get('day')
        session_type = request.form.get('session')
        
        if not day or not session_type:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Please select a day and session.'})
            else:
                flash('Please select a day and session.', 'warning')
                return redirect(url_for('tournaments.list_tournaments'))
        
        # Store attendance info
        attending[tournament_id] = {
            'date': day,
            'session': session_type
        }
        
        message = f"You're attending {tournament.name} on {day} for the {session_type} session!"
        if is_ajax:
            return jsonify({'success': True, 'message': message})
        else:
            flash(message, 'success')
    
    # Update user record
    user.attending = attending
    db.session.commit()
    
    if is_ajax:
        return jsonify({'success': True})
    else:
        return redirect(url_for('tournaments.list_tournaments'))

@tournaments_bp.route('/tournaments/<tournament_id>/raise_hand', methods=['POST'])
@login_required
def raise_hand(tournament_id):
    # Get form data
    day = request.form.get('day')
    session_type = request.form.get('session')
    
    # Validate tournament exists
    tournament = Tournament.query.get(tournament_id)
    
    if not tournament:
        flash('Tournament not found.', 'danger')
        return redirect(url_for('tournaments.list_tournaments'))
    
    # Update user's raised hand
    user = User.query.get(current_user.id)
    raised_hand = dict(user.raised_hand) if user.raised_hand else {}
    
    # If raising hand
    if day and session_type:
        raised_hand[tournament_id] = {"day": day, "session": session_type}
        flash("You've raised your hand for this tournament. Other fans can now see you're open to meet!", 'success')
    # If lowering hand
    else:
        if tournament_id in raised_hand:
            del raised_hand[tournament_id]
            flash("You've lowered your hand for this tournament.", 'info')
    
    user.raised_hand = raised_hand
    db.session.commit()
    
    return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))
