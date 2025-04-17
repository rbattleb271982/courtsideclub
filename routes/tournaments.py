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
    # Get all tournaments for dropdown options
    all_tournaments = Tournament.query.all()
    
    # Initialize query
    query = Tournament.query
    
    # Get name filter parameter
    name_filter = request.args.get('name')
    
    # Apply name filter if provided
    if name_filter:
        query = query.filter(Tournament.id == name_filter)
    
    # Get the filtered tournaments
    tournaments = query.all()
    
    # Get today's date for highlighting current tournaments
    today = datetime.datetime.now().date()
    
    return render_template('tournaments.html', 
                          tournaments=tournaments,
                          all_tournaments=all_tournaments,
                          today=today,
                          name_filter=name_filter)

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
        User.raised_hand.contains({tournament_id: {}})
    ).all()
    
    for user in users_with_raised_hands:
        if tournament_id in user.raised_hand:
            # Format each day and session for display
            for day, sessions in user.raised_hand[tournament_id].items():
                sessions_str = ", ".join(sessions)
                raised_hands.append({
                    'name': user.get_full_name(),
                    'email': user.email,
                    'day': day,
                    'sessions': sessions_str,
                    'user_id': user.id
                })
    
    # Check if current user is attending
    user_attending = tournament_id in current_user.attending
    
    # Check if current user has raised hand
    user_raised_hand = tournament_id in current_user.raised_hand
    
    return render_template('tournament_detail.html',
                          tournament=tournament,
                          user_attending=user_attending,
                          user_raised_hand=user_raised_hand,
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
        # The new format: raised_hand[tournament_id][Day X][] = [Day, Night]
        attendance = {}
        
        # Process the form data
        for field_name, value in request.form.items():
            # Check if this is a raised_hand field for this tournament
            # Note: The form uses raised_hand name but we're storing in the attending dictionary
            if field_name.startswith(f'raised_hand[{tournament_id}]'):
                # Extract the day key from the field name
                # Format: raised_hand[tournament_id][Day X][]
                parts = field_name.split('[')
                if len(parts) >= 3:
                    day_key = parts[2].rstrip(']')
                    session_value = value
                    
                    # Initialize the day entry if it doesn't exist
                    if day_key not in attendance:
                        attendance[day_key] = []
                    
                    # Add this session to the day
                    attendance[day_key].append(session_value)
        
        # Check if any selections were made
        if not attendance:
            if is_ajax:
                return jsonify({'success': False, 'message': 'Please select at least one day and session.'})
            else:
                flash('Please select at least one day and session.', 'warning')
                return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))
        
        # Store attendance info with the new format
        attending[tournament_id] = attendance
        
        # Format a readable message about the selections
        day_session_parts = []
        for day, sessions in attendance.items():
            sessions_str = " and ".join(sessions)
            day_session_parts.append(f"{day} ({sessions_str})")
        
        selections = ", ".join(day_session_parts)
        message = f"You're attending {tournament.name}: {selections}"
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
        return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))

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
        # Use the 'Day X' format to be consistent with attendance data
        day_key = f"Day {day}"
        
        # Initialize or update this tournament's raised hand data
        if tournament_id not in raised_hand:
            raised_hand[tournament_id] = {}
        
        # Store the session for this day
        if day_key not in raised_hand[tournament_id]:
            raised_hand[tournament_id][day_key] = []
        
        # Add the session type
        if session_type not in raised_hand[tournament_id][day_key]:
            raised_hand[tournament_id][day_key].append(session_type)
        
        flash("You've raised your hand for this tournament. Other fans can now see you're open to meet!", 'success')
    # If lowering hand
    else:
        if tournament_id in raised_hand:
            del raised_hand[tournament_id]
            flash("You've lowered your hand for this tournament.", 'info')
    
    user.raised_hand = raised_hand
    db.session.commit()
    
    return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))
