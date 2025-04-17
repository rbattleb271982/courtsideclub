from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from replit import db
import datetime

# Initialize blueprint
tournaments_bp = Blueprint('tournaments', __name__)

@tournaments_bp.route('/')
def index():
    return redirect(url_for('tournaments.list_tournaments'))

@tournaments_bp.route('/tournaments')
@login_required
def list_tournaments():
    # Get all tournaments
    tournaments = db.get('tournaments', [])
    
    # Filter by date if requested
    date_filter = request.args.get('date')
    if date_filter:
        try:
            filter_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
            tournaments = [t for t in tournaments if 
                          datetime.datetime.strptime(t['start_date'], '%Y-%m-%d').date() <= filter_date <= 
                          datetime.datetime.strptime(t['end_date'], '%Y-%m-%d').date()]
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'warning')
    
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
    tournaments = db.get('tournaments', [])
    tournament = next((t for t in tournaments if t['id'] == tournament_id), None)
    
    if not tournament:
        flash('Tournament not found.', 'danger')
        return redirect(url_for('tournaments.list_tournaments'))
    
    # Get users who raised hands for this tournament
    raised_hands = []
    for user_key in db.keys():
        user_data = db.get(user_key)
        if (isinstance(user_data, dict) and 
            user_data.get('raised_hand') and 
            tournament_id in user_data.get('raised_hand', {})):
            
            raised_hands.append({
                'name': user_data.get('name'),
                'email': user_data.get('email'),
                'day': user_data['raised_hand'][tournament_id].get('day'),
                'session': user_data['raised_hand'][tournament_id].get('session')
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
    tournaments = db.get('tournaments', [])
    tournament = next((t for t in tournaments if t['id'] == tournament_id), None)
    
    if not tournament:
        flash('Tournament not found.', 'danger')
        return redirect(url_for('tournaments.list_tournaments'))
    
    # Update user's attending list
    user_data = db.get(current_user.id, {})
    attending = user_data.get('attending', [])
    
    if tournament_id in attending:
        attending.remove(tournament_id)
        flash(f"You're no longer attending {tournament['name']}.", 'info')
    else:
        attending.append(tournament_id)
        flash(f"You're now attending {tournament['name']}!", 'success')
    
    user_data['attending'] = attending
    db[current_user.id] = user_data
    
    return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))

@tournaments_bp.route('/tournaments/<tournament_id>/raise_hand', methods=['POST'])
@login_required
def raise_hand(tournament_id):
    # Get form data
    day = request.form.get('day')
    session_type = request.form.get('session')
    
    # Validate tournament exists
    tournaments = db.get('tournaments', [])
    tournament = next((t for t in tournaments if t['id'] == tournament_id), None)
    
    if not tournament:
        flash('Tournament not found.', 'danger')
        return redirect(url_for('tournaments.list_tournaments'))
    
    # Update user's raised hand
    user_data = db.get(current_user.id, {})
    raised_hand = user_data.get('raised_hand', {})
    
    # If raising hand
    if day and session_type:
        raised_hand[tournament_id] = {"day": day, "session": session_type}
        flash("You've raised your hand for this tournament. Other fans can now see you're open to meet!", 'success')
    # If lowering hand
    else:
        if tournament_id in raised_hand:
            del raised_hand[tournament_id]
            flash("You've lowered your hand for this tournament.", 'info')
    
    user_data['raised_hand'] = raised_hand
    db[current_user.id] = user_data
    
    return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))
