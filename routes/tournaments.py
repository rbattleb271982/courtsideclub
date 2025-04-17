import datetime
import json
try:
    from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
    from flask_login import login_required, current_user
except ImportError:
    pass  # Imports will be available at runtime
    
from models import db, User, Tournament

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
    
    # Initialize query with chronological sorting by start date
    query = Tournament.query.order_by(Tournament.start_date)
    
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
        # Count users who have selected any day/session for this tournament
        attending_users = User.query.filter(
            User.raised_hand.contains({tournament.id: {}})
        ).count()
        
        # For now, all users with raised_hand are counted as open to meeting
        meeting_users = attending_users
        
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
    
    # Calculate overall attendance and meetup counts
    # Count any user with the tournament in their attending field
    # Don't include the current user unless they've already saved preferences
    if tournament_id not in current_user.attending:
        # Current user isn't counted yet since they haven't saved
        attending_count = User.query.filter(
            User.attending.contains({tournament_id: {}})
        ).count()
    else:
        # Include all users with this tournament in their attending field
        attending_count = User.query.filter(
            User.attending.contains({tournament_id: {}})
        ).count()
    
    # Count any user with the tournament in their raised_hand field
    # Don't include the current user unless they've already set preferences
    if tournament_id not in current_user.raised_hand:
        # Current user isn't counted yet since they haven't saved
        meeting_count = User.query.filter(
            User.raised_hand.contains({tournament_id: {}})
        ).count()
    else:
        meeting_count = User.query.filter(
            User.raised_hand.contains({tournament_id: {}})
        ).count()
    
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
    
    # Count attendance per day and session
    for user in users_with_raised_hands:
        if tournament_id in user.raised_hand:
            for day, sessions in user.raised_hand[tournament_id].items():
                if day in day_attendance:
                    # Increment day counter
                    day_attendance[day]['attending'] += 1
                    day_attendance[day]['meeting'] += 1  # All raisedHand users count as meeting for now
                    
                    # Increment session counters
                    for session in sessions:
                        if session in day_attendance[day]['sessions']:
                            day_attendance[day]['sessions'][session]['attending'] += 1
                            day_attendance[day]['sessions'][session]['meeting'] += 1
    
    # Check if current user is attending
    user_attending = tournament_id in current_user.attending
    
    # Check if current user has raised hand
    user_raised_hand = tournament_id in current_user.raised_hand
    
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
    
    # Update user's attending information
    user = User.query.get(current_user.id)
    attending = dict(user.attending) if user.attending else {}
    
    # Check if this is a removal request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    remove = request.form.get('remove') == 'true'
    
    if remove:
        if tournament_id in attending:
            # Remove from attending dictionary
            del attending[tournament_id]
            
            # Also remove from raised_hand if present
            raised_hand = dict(user.raised_hand) if user.raised_hand else {}
            if tournament_id in raised_hand:
                del raised_hand[tournament_id]
                user.raised_hand = raised_hand
            
            # Update user record before returning
            user.attending = attending
            db.session.commit()
            
            message = f"You're no longer attending {tournament.name}."
            if is_ajax:
                return jsonify({'success': True, 'message': message})
            else:
                flash(message, 'info')
                return redirect(url_for('tournaments.list_tournaments'))
    else:
        # Handle simple "I'm attending" checkbox from tournaments list
        attending_checkbox = request.form.get('attending') == 'true'
        
        if attending_checkbox:
            # Mark as attending with empty session details
            # Sessions will be selected on the tournament detail page
            attending[tournament_id] = {}
            message = f"You're attending {tournament.name}! Please select your sessions."
            
            user.attending = attending
            db.session.commit()
            
            # Redirect to tournament detail page to select sessions
            flash(message, 'success')
            return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))
            
        # Handle session selections and meeting preferences from the session form
        elif 'sessions' in request.form:
            attendance = {}
            
            # Process the session form data
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
                            if day_key not in attendance:
                                attendance[day_key] = []
                            attendance[day_key].append(session_type)
            
            # Check for meeting preference in the same form
            meeting_preference = request.form.get('meeting_preference')
            
            # Update raised_hand status based on meeting preference
            raised_hand = dict(user.raised_hand) if user.raised_hand else {}
            
            # Store attendance info
            # If sessions were selected, update both attending and raised_hand
            if attendance:
                attending[tournament_id] = attendance
                
                # Also update raised_hand with same session data if "Yes" to meeting
                if meeting_preference == 'Yes':
                    raised_hand[tournament_id] = attendance
                else:
                    # If "No" to meeting but previously raised hand, remove it
                    if tournament_id in raised_hand:
                        del raised_hand[tournament_id]
                        
                message = f"Your selections for {tournament.name} have been saved!"
            else:
                # No sessions were selected
                # Either remove attendance or keep empty based on preference
                if meeting_preference:  # If form included meeting preference
                    if tournament_id in attending:
                        del attending[tournament_id]
                    if tournament_id in raised_hand:
                        del raised_hand[tournament_id]
                    message = f"You're no longer attending {tournament.name}."
                else:
                    # Just keep as attending with no sessions
                    attending[tournament_id] = {}
                    message = f"You're attending {tournament.name}!"
                
            if is_ajax:
                return jsonify({'success': True, 'message': message})
            else:
                flash(message, 'success')
                
                # Save the changes and redirect to home page after saving sessions
                user.raised_hand = raised_hand
                # Update user record
                user.attending = attending
                db.session.commit()
                
                if is_ajax:
                    return jsonify({'success': True, 'message': message})
                else:
                    # Redirect to home page after saving sessions
                    return redirect(url_for('user.home'))
        else:
            # Default behavior - just mark them as attending
            attending[tournament_id] = {}
            message = f"You're attending {tournament.name}!"
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

@tournaments_bp.route('/tournaments/past', methods=['GET', 'POST'])
@login_required
def past_tournaments():
    # Get all tournaments for the list, sorted alphabetically by name
    all_tournaments = Tournament.query.order_by(Tournament.name).all()
    
    # Get the user's past tournaments list
    user = User.query.get(current_user.id)
    past_tournaments = list(user.past_tournaments) if user.past_tournaments else []
    
    # Handle form submission
    if request.method == 'POST':
        # Reset the past_tournaments list
        past_tournaments = []
        
        # Process checked tournaments
        for field_name, value in request.form.items():
            if field_name.startswith('tournament_'):
                # Extract tournament_id from field name (format: tournament_<id>)
                tournament_id = field_name.split('_', 1)[1]
                
                # Add to the list if checked
                if value == 'on':
                    past_tournaments.append(tournament_id)
        
        # Update user's past_tournaments
        user.past_tournaments = past_tournaments
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
    
    # Check if the user is attending this tournament
    user = User.query.get(current_user.id)
    if tournament_id not in user.attending:
        flash("You need to mark yourself as attending this tournament before setting meeting preferences.", 'warning')
        return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))
    
    # Update user's raised hand status
    raised_hand = dict(user.raised_hand) if user.raised_hand else {}
    
    # If open to meeting ("Yes")
    if meeting_pref == 'Yes':
        # Copy the attendance data from the attending field to the raised_hand field
        # This will either have day/session data or be an empty dict
        attending_data = user.attending.get(tournament_id, {})
        raised_hand[tournament_id] = attending_data
        flash("You're now visible as open to meeting other fans at this tournament!", 'success')
    # If not open to meeting ("No") or reset
    else:
        if tournament_id in raised_hand:
            del raised_hand[tournament_id]
            if meeting_pref == 'No':
                flash("You're marked as not open to meeting at this tournament.", 'info')
            else:
                flash("Your meeting preference has been reset.", 'info')
    
    user.raised_hand = raised_hand
    db.session.commit()
    
    return redirect(url_for('tournaments.tournament_detail', tournament_id=tournament_id))
