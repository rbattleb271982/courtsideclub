from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify, make_response
from flask_login import login_required, current_user
from models import db, Tournament, UserTournament, User, Event, ShippingAddress
from sqlalchemy import func, desc
from utils.event_meta import event_descriptions
import csv
import io
from datetime import datetime, timedelta

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))

    try:
        # Get today's date for comparison
        today = datetime.now().date()
        tournaments = Tournament.query.order_by(Tournament.start_date).all()
        dashboard_data = []

        for tournament in tournaments:
            # Count total registrations for this tournament
            total_registrations = UserTournament.query.filter_by(tournament_id=tournament.id).count()
            
            # Count attending (saved sessions)
            attending_count = UserTournament.query.filter_by(
                tournament_id=tournament.id, 
                attending=True
            ).count()
            
            # Count open to meet
            open_to_meet_count = UserTournament.query.filter_by(
                tournament_id=tournament.id,
                wants_to_meet=True
            ).count()
            
            # Get session breakdown
            session_counts = {}
            
            # Query for all user_tournaments with sessions
            user_tourneys = UserTournament.query.filter_by(
                tournament_id=tournament.id,
                attending=True
            ).all()
            
            # Process session labels
            day_count = 0
            night_count = 0
            
            for ut in user_tourneys:
                if not ut.session_label:
                    continue
                    
                sessions = [s.strip() for s in ut.session_label.split(',') if s.strip()]
                for session in sessions:
                    if 'Day' in session:
                        day_count += 1
                    elif 'Night' in session:
                        night_count += 1
            
            # Count lanyard orders
            lanyard_count = UserTournament.query.join(User).filter(
                UserTournament.tournament_id == tournament.id,
                User.lanyard_ordered == True
            ).count()
            
            # Prepare data for the dashboard
            dashboard_data.append({
                'tournament': tournament,
                'total_registrations': total_registrations,
                'total_attending': attending_count,
                'total_meetups': open_to_meet_count,
                'total_lanyards': lanyard_count,
                'day_count': day_count,
                'night_count': night_count,
                'start_date_unix': datetime.combine(tournament.start_date, datetime.min.time()).timestamp() if tournament.start_date else 0
            })

        # Sort tournaments by start date
        # Use try/except for timestamp conversion to avoid datetime errors
        def safe_sort_key(item):
            try:
                return item['start_date_unix']
            except (TypeError, AttributeError):
                return 0
                
        dashboard_data.sort(key=safe_sort_key)
        
        return render_template('admin_dashboard.html', dashboard_data=dashboard_data)
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "danger")
        return render_template('admin_dashboard.html', dashboard_data=[])

@admin_bp.route('/tournament/<tournament_slug>', methods=['GET'])
@login_required
def view_tournament(tournament_slug):
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))

    try:
        tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
        
        # Get session statistics
        # We'll track Day vs. Night attendance by session type (Day 1, Day 2, etc.)
        session_stats = {}
        
        # Initialize stats for all possible tournament days (typically 14 days for a Grand Slam)
        # This ensures we show all days in the grid, even those with zero attendees
        tournament_duration = (tournament.end_date - tournament.start_date).days + 1
        max_days = 14 if tournament.event_type == "Grand Slam" else tournament_duration
        
        # Pre-populate all days with zero counts
        for day in range(1, max_days + 1):
            session_stats[day] = {'Day': 0, 'Night': 0, 'Total': 0}
            
        # Get all user tournaments with sessions
        user_tourneys = UserTournament.query.filter_by(
            tournament_id=tournament.id,
            attending=True
        ).all()
        
        # Process session labels
        for ut in user_tourneys:
            if not ut.session_label:
                continue
                
            sessions = [s.strip() for s in ut.session_label.split(',') if s.strip()]
            for session in sessions:
                session_type = 'Other'
                if 'Day' in session:
                    session_type = 'Day'
                elif 'Night' in session:
                    session_type = 'Night'
                    
                # Extract the day number (if present)
                day_num = None
                parts = session.split()
                for part in parts:
                    if part.isdigit():
                        day_num = int(part)
                        break
                
                # Use day number or just the session name without 'Day'/'Night'
                session_key = day_num if day_num else session.replace('Day', '').replace('Night', '').strip()
                
                # Skip if session_key is not a number or is outside our range
                if not isinstance(session_key, int) or session_key < 1 or session_key > max_days:
                    continue
                    
                session_stats[session_key][session_type] += 1
                session_stats[session_key]['Total'] += 1
        
        # Sort by day number
        sorted_sessions = sorted(session_stats.items(), key=lambda x: (
            # Try to convert to int for numerical sorting, fall back to string
            int(x[0]) if isinstance(x[0], (int, str)) and str(x[0]).isdigit() else float('inf'), 
            str(x[0])
        ))
        
        # Calculate row and column totals
        day_total = sum(stats['Day'] for _, stats in sorted_sessions)
        night_total = sum(stats['Night'] for _, stats in sorted_sessions)
        grand_total = day_total + night_total
        
        # Get attendee information for expandable section
        attendees = UserTournament.query.filter_by(
            tournament_id=tournament.id,
            attending=True
        ).join(User).all()
        
        # Prepare attendee data
        attendee_data = []
        for attendance in attendees:
            sessions = attendance.session_label if attendance.session_label else "None"
            wants_to_meet = "Yes" if attendance.wants_to_meet else "No"
            
            user = User.query.get(attendance.user_id)
            if user:
                attendee_data.append({
                    'id': user.id,
                    'name': user.get_full_name(),
                    'email': user.email,
                    'sessions': sessions,
                    'wants_to_meet': wants_to_meet,
                    'lanyard': "Ordered" if user.lanyard_ordered else "No"
                })
        
        # Sort attendees by name
        attendee_data.sort(key=lambda x: x['name'].lower())
        
        return render_template(
            'admin_tournament_detail.html',
            tournament=tournament,
            session_stats=sorted_sessions,
            day_total=day_total,
            night_total=night_total,
            grand_total=grand_total,
            attendees=attendee_data
        )
    except Exception as e:
        flash(f"Error loading tournament details: {str(e)}", "danger")
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/tournament/<tournament_slug>/attendees')
@login_required
def view_attendees(tournament_slug):
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
        
    try:
        tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
        
        # Get sort parameters
        sort_by = request.args.get('sort', 'name')
        sort_dir = request.args.get('dir', 'asc')
        
        # Get attendee information
        attendees_query = (
            db.session.query(User, UserTournament)
            .join(UserTournament, User.id == UserTournament.user_id)
            .filter(
                UserTournament.tournament_id == tournament.id,
                UserTournament.attending == True
            )
        )
        
        # Apply sorting
        if sort_by == 'name':
            if sort_dir == 'asc':
                attendees_query = attendees_query.order_by(User.first_name, User.last_name)
            else:
                attendees_query = attendees_query.order_by(User.first_name.desc(), User.last_name.desc())
        elif sort_by == 'email':
            if sort_dir == 'asc':
                attendees_query = attendees_query.order_by(User.email)
            else:
                attendees_query = attendees_query.order_by(User.email.desc())
        
        attendees = attendees_query.all()
        
        # Prepare attendee data
        attendee_data = []
        for user, attendance in attendees:
            sessions = attendance.session_label if attendance.session_label else "None"
            wants_to_meet = "Yes" if attendance.wants_to_meet else "No"
            
            attendee_data.append({
                'id': user.id,
                'name': user.get_full_name(),
                'email': user.email,
                'sessions': sessions,
                'wants_to_meet': wants_to_meet,
                'lanyard': "Ordered" if user.lanyard_ordered else "No"
            })
        
        return render_template(
            'admin_attendees.html',
            tournament=tournament,
            attendees=attendee_data,
            sort_by=sort_by,
            sort_dir=sort_dir
        )
    except Exception as e:
        flash(f"Error loading attendees: {str(e)}", "danger")
        return redirect(url_for('admin.view_tournament', tournament_slug=tournament_slug))

@admin_bp.route('/tournaments')
@login_required
def list_tournaments():
    """Admin view to list all tournaments for editing"""
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
        
    tournaments = Tournament.query.order_by(Tournament.start_date).all()
    return render_template('admin_tournaments.html', tournaments=tournaments)

@admin_bp.route('/tournament/<tournament_slug>/update', methods=['POST'])
@login_required
def update_tournament(tournament_slug):
    """Inline update of tournament details"""
    try:
        if not current_user.is_admin:
            flash("Access denied.", "danger")
            return redirect(url_for("main.public_home"))
            
        tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
        
        # Update tournament details - handle empty input correctly
        tournament.about = request.form.get('about', '').strip()
        
        # Handle URL fields with https:// prefix
        draw_url_input = request.form.get('draw_url', '').strip()
        if draw_url_input:
            # Ensure URL has https:// prefix
            if not draw_url_input.startswith('http'):
                tournament.draw_url = f"https://{draw_url_input}"
            else:
                tournament.draw_url = draw_url_input
        else:
            tournament.draw_url = None
        
        schedule_url_input = request.form.get('schedule_url', '').strip()
        if schedule_url_input:
            # Ensure URL has https:// prefix
            if not schedule_url_input.startswith('http'):
                tournament.schedule_url = f"https://{schedule_url_input}"
            else:
                tournament.schedule_url = schedule_url_input
        else:
            tournament.schedule_url = None
        
        # Update surface if provided
        surface = request.form.get('surface', '').strip()
        tournament.surface = surface if surface else None
        
        db.session.commit()
        
        # Log the event using our standardized event logging service
        from services.event_logger import log_event
        
        # Track which fields were actually updated
        updated_fields = []
        if request.form.get('about', '').strip() != '':
            updated_fields.append('about')
        if request.form.get('draw_url', '').strip() != '':
            updated_fields.append('draw_url')
        if request.form.get('schedule_url', '').strip() != '':
            updated_fields.append('schedule_url')
        if request.form.get('surface', '').strip() != '':
            updated_fields.append('surface')
            
        log_event('admin_tournament_updated', data={
            'tournament_id': tournament.id,
            'tournament_name': tournament.name,
            'tournament_slug': tournament.slug,
            'fields_updated': updated_fields,
            'admin_user': current_user.email,
            'ip': request.remote_addr,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        flash(f"Tournament '{tournament.name}' has been updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating tournament: {str(e)}", "danger")
    
    # Return to the tournament detail page
    return redirect(url_for('admin.view_tournament', tournament_slug=tournament_slug))

@admin_bp.route('/events')
@login_required
def view_events():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Get optional date filter parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Default to last 7 days if no dates specified
    today = datetime.utcnow().date()
    if not start_date_str:
        start_date = today - timedelta(days=7)
    else:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=7)
            flash("Invalid start date format. Showing last 7 days instead.", "warning")
    
    if not end_date_str:
        end_date = today
    else:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
            flash("Invalid end date format. Using today instead.", "warning")
    
    # Add time to make the date range inclusive
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Calculate previous and next periods for navigation
    period_length = (end_date - start_date).days or 1  # Ensure at least 1 day
    prev_start = start_date - timedelta(days=period_length)
    prev_end = start_date - timedelta(days=1)
    next_start = end_date + timedelta(days=1)
    next_end = end_date + timedelta(days=period_length)
    
    # Option to view summary or raw logs
    view_type = request.args.get('view', 'summary')
    
    if view_type == 'summary':
        return view_event_log()
    else:
        # Get event counts per type
        events = Event.query.filter(
            Event.timestamp.between(start_datetime, end_datetime)
        ).order_by(Event.timestamp.desc()).all()
        
        return render_template(
            'admin_events.html',
            events=events,
            start_date=start_date,
            end_date=end_date,
            prev_start=prev_start,
            prev_end=prev_end,
            next_start=next_start,
            next_end=next_end,
            view_type=view_type
        )

@admin_bp.route('/events/log')
@login_required
def view_event_log():
    """Shows event log summary instead of raw events"""
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Define all expected event types (using our event_descriptions dictionary)
    expected_events = list(event_descriptions.keys())
    
    # Get actual event counts from the database
    db_event_counts = db.session.query(
        Event.name, 
        func.count(Event.id).label('count')
    ).group_by(Event.name).all()
    
    # Convert query result to a dictionary for easier lookup
    count_dict = {event_name: count for event_name, count in db_event_counts}
    
    # Prepare event data with descriptions, including 0-count events
    event_summary = []
    total_events = 0
    
    # First, add all events that have counts in the database
    for event_name, count in count_dict.items():
        description = event_descriptions.get(event_name, "User action")
        total_events += count
        
        event_summary.append({
            'name': event_name,
            'count': count,
            'description': description
        })
    
    # Then add any expected events that weren't found in the database (with count 0)
    for event_name in expected_events:
        if event_name not in count_dict:
            description = event_descriptions.get(event_name, "User action")
            event_summary.append({
                'name': event_name,
                'count': 0,
                'description': description
            })
    
    # Get sorting parameters
    sort_by = request.args.get('sort_by', 'count')
    sort_dir = request.args.get('sort_dir', 'desc')
    
    # Apply sorting
    if sort_by == 'name':
        event_summary.sort(key=lambda x: x['name'].lower(), reverse=(sort_dir == 'desc'))
    elif sort_by == 'count':
        event_summary.sort(key=lambda x: x['count'], reverse=(sort_dir == 'desc'))
    elif sort_by == 'description':
        event_summary.sort(key=lambda x: x['description'].lower(), reverse=(sort_dir == 'desc'))
    
    return render_template(
        'admin_event_summary.html',
        event_summary=event_summary,
        total_events=total_events,
        sort_by=sort_by,
        sort_dir=sort_dir
    )

@admin_bp.route('/export-event-log')
@login_required
def export_event_log():
    """Export event log summary data as CSV"""
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Get optional date filter parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Default to last 30 days if no dates specified
    today = datetime.utcnow().date()
    if not start_date_str:
        start_date = today - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    
    if not end_date_str:
        end_date = today
    else:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    
    # Add time to make the date range inclusive
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Define descriptions for common event types
    event_descriptions = {
        "tournament_view": "Viewed a tournament page",
        "tournament_register": "Registered for a tournament",
        "lanyard_order": "Ordered a lanyard",
        "login": "User logged in",
        "profile_update": "Updated profile information",
        "session_select": "Selected tournament session(s)",
        "session_deselect": "Deselected tournament session(s)",
        "welcome_seen": "Viewed welcome message",
        "password_reset": "Requested password reset",
        "user_registration": "New user registration",
        "past_tournament_add": "Added past tournament",
        "past_tournament_remove": "Removed past tournament"
    }
    
    # Get raw events with user details
    events = db.session.query(
        Event.id,
        Event.name,
        Event.timestamp,
        User.email
    ).join(User, User.id == Event.user_id).filter(
        Event.timestamp.between(start_datetime, end_datetime)
    ).order_by(Event.timestamp.desc()).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Event ID', 'Event Type', 'Description', 'User Email', 'Date'])
    
    for event_id, event_name, event_date, user_email in events:
        description = event_descriptions.get(event_name, "User action")
        writer.writerow([
            event_id,
            event_name,
            description,
            user_email,
            event_date.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    output.seek(0)
    return Response(
        output, 
        mimetype="text/csv", 
        headers={"Content-Disposition": "attachment;filename=event_log.csv"}
    )

@admin_bp.route('/event-types')
@login_required
def view_event_types():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Get event counts per type
    event_counts = db.session.query(
        Event.name, 
        func.count(Event.id).label('count')
    ).group_by(Event.name).order_by(desc('count')).all()
    
    # Prepare event data with descriptions
    event_data = []
    for event_name, count in event_counts:
        # Use the imported comprehensive event descriptions dictionary
        description = event_descriptions.get(event_name, "User action")
        
        event_data.append({
            'name': event_name,
            'count': count,
            'description': description
        })
    
    return render_template('admin_event_types.html', event_data=event_data)

@admin_bp.route('/event-summary')
@login_required
def event_summary():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Define descriptions for common event types
    event_descriptions = {
        "tournament_view": "Viewed a tournament page",
        "tournament_register": "Registered for a tournament",
        "lanyard_order": "Ordered a lanyard",
        "login": "User logged in",
        "profile_update": "Updated profile information",
        "session_select": "Selected tournament session(s)",
        "session_deselect": "Deselected tournament session(s)",
        "welcome_seen": "Viewed welcome message",
        "password_reset": "Requested password reset",
        "user_registration": "New user registration",
        "past_tournament_add": "Added past tournament",
        "past_tournament_remove": "Removed past tournament"
    }
    
    # Get event counts per type
    event_counts = db.session.query(
        Event.name, 
        func.count(Event.id).label('count')
    ).group_by(Event.name).order_by(desc('count')).all()
    
    # Prepare event data with descriptions
    event_data = []
    for event_name, count in event_counts:
        description = event_descriptions.get(event_name, "User action")
        
        event_data.append({
            'name': event_name,
            'count': count,
            'description': description
        })
    
    return render_template('admin_event_summary.html', event_data=event_data)

@admin_bp.route('/export-event-summary')
@login_required
def export_event_summary():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Define descriptions 
    event_descriptions = {
        "tournament_view": "Viewed a tournament page",
        "tournament_register": "Registered for a tournament",
        "lanyard_order": "Ordered a lanyard",
        "login": "User logged in",
        "profile_update": "Updated profile information",
        "session_select": "Selected tournament session(s)",
        "session_deselect": "Deselected tournament session(s)",
        "welcome_seen": "Viewed welcome message",
        "password_reset": "Requested password reset",
        "user_registration": "New user registration",
        "past_tournament_add": "Added past tournament",
        "past_tournament_remove": "Removed past tournament"
    }
    
    # Get event counts
    event_counts = db.session.query(
        Event.name, 
        func.count(Event.id).label('count')
    ).group_by(Event.name).order_by(desc('count')).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Event Name', 'Count', 'Description'])
    
    for event_name, count in event_counts:
        description = event_descriptions.get(event_name, "User action")
        writer.writerow([event_name, count, description])
    
    output.seek(0)
    return Response(
        output, 
        mimetype="text/csv", 
        headers={"Content-Disposition": "attachment;filename=event_summary.csv"}
    )

# Added implementation for lanyard fulfillment page
@admin_bp.route('/lanyards')
@login_required
def lanyard_fulfillment():
    """Admin view for lanyard fulfillment tracking"""
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Get all users who ordered lanyards
    users_with_lanyards = User.query.filter_by(lanyard_ordered=True).all()
    
    # Summary stats
    total_ordered = len(users_with_lanyards)
    total_sent = sum(1 for user in users_with_lanyards if user.lanyard_sent)
    total_not_sent = total_ordered - total_sent
    
    # Find the next upcoming tournament
    today = datetime.utcnow().date()
    next_tournament = Tournament.query.filter(Tournament.start_date >= today).order_by(Tournament.start_date).first()
    
    # Get all tournaments for dropdown filter
    all_tournaments = Tournament.query.filter(Tournament.start_date >= today).order_by(Tournament.start_date).all()
    
    # Users with unsent lanyards who are attending the next tournament
    unsent_next_tournament = []
    if next_tournament:
        for user in users_with_lanyards:
            if not user.lanyard_sent:
                # Check if user is attending next tournament
                registration = UserTournament.query.filter_by(
                    user_id=user.id,
                    tournament_id=next_tournament.id,
                    attending=True
                ).first()
                
                if registration:
                    unsent_next_tournament.append(user)
    
    # Prepare lanyard fulfillment data
    lanyard_data = []
    
    # Dictionary to store other tournaments by user
    other_tournaments = {}
    
    for user in users_with_lanyards:
        # Get shipping address if available
        has_address = bool(ShippingAddress.query.filter_by(user_id=user.id).first())
        
        # Get all tournaments the user is attending, ordered by date
        user_tourneys = UserTournament.query.filter_by(
            user_id=user.id,
            attending=True
        ).join(Tournament).order_by(Tournament.start_date).all()
        
        # Handle first tournament and other tournaments
        first_tournament = None
        first_tournament_date = None
        sessions = None
        
        if user_tourneys:
            # First tournament
            first_tournament = Tournament.query.get(user_tourneys[0].tournament_id)
            if first_tournament:
                first_tournament_date = first_tournament.start_date
                sessions = user_tourneys[0].session_label
            
            # Other tournaments (limited to 3 for display)
            if len(user_tourneys) > 1:
                other_names = []
                for i in range(1, min(4, len(user_tourneys))):
                    t = Tournament.query.get(user_tourneys[i].tournament_id)
                    if t:
                        other_names.append(t.name)
                
                # Add ellipsis if more than 3 other tournaments
                if len(user_tourneys) > 4:
                    other_names.append("...")
                
                other_tournaments[user.id] = ", ".join(other_names)
        
        lanyard_data.append({
            'user': user,
            'has_address': has_address,
            'first_tournament': first_tournament,
            'first_tournament_date': first_tournament_date,
            'sessions': sessions
        })
    
    # Sort by lanyard_sent (unsent first), then by first tournament date
    lanyard_data.sort(key=lambda x: (
        x['user'].lanyard_sent,  # False comes before True
        x['first_tournament_date'] if x['first_tournament_date'] else datetime(9999, 12, 31).date()  # Sort by tournament date
    ))
    
    # Helper function for template to get shipping address details
    def get_shipping_address(user_id):
        """Get shipping address for display in template"""
        return ShippingAddress.query.filter_by(user_id=user_id).first()
    
    return render_template(
        "admin_lanyard_fulfillment.html",
        lanyard_data=lanyard_data,
        total_ordered=total_ordered,
        total_sent=total_sent,
        total_not_sent=total_not_sent,
        next_tournament=next_tournament,
        unsent_next_tournament=unsent_next_tournament,
        tournaments=all_tournaments,
        other_tournaments=other_tournaments,
        get_shipping_address=get_shipping_address,
        today_date=datetime.utcnow().date()
    )

@admin_bp.route('/lanyards/update-status/<int:user_id>', methods=['POST'])
@login_required
def update_lanyard_status(user_id):
    """Update lanyard fulfillment status"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    status = request.form.get('status') == 'true'
    
    # Update user's lanyard status
    user.lanyard_sent = status
    
    # If marking as sent, record the timestamp
    if status:
        user.lanyard_sent_date = datetime.utcnow()
    else:
        user.lanyard_sent_date = None
    
    # Save changes
    db.session.commit()
    
    # Log the event using standardized event logging
    from services.event_logger import log_event
    
    # Get recipient's email and first tournament for better tracking
    recipient_email = user.email
    
    # Find recipient's first tournament (if any)
    first_tournament = None
    user_tourneys = UserTournament.query.filter_by(
        user_id=user.id,
        attending=True
    ).join(Tournament).order_by(Tournament.start_date).first()
    
    if user_tourneys:
        first_tournament = Tournament.query.get(user_tourneys.tournament_id)
    
    # Log the event with detailed metadata
    log_event('lanyard_marked_sent' if status else 'lanyard_marked_unsent', data={
        "target_user_id": user_id,
        "target_user_email": recipient_email,
        "admin_user": current_user.email,
        "tournament_id": first_tournament.id if first_tournament else None,
        "tournament_name": first_tournament.name if first_tournament else None,
        "ip": request.remote_addr,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return jsonify({
        'success': True, 
        'sent': status,
        'date': user.lanyard_sent_date.strftime('%b %d, %Y %H:%M UTC') if user.lanyard_sent_date else None
    })

@admin_bp.route('/lanyards/address/<int:user_id>')
@login_required
def get_shipping_address_detail(user_id):
    """Get detailed shipping address for a user"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    address = ShippingAddress.query.filter_by(user_id=user_id).first()
    
    if not address:
        return jsonify({'success': False, 'message': 'No address found for this user'}), 404
    
    # Return address details as JSON
    return jsonify({
        'success': True,
        'address': {
            'name': address.name,
            'address1': address.address1,
            'address2': address.address2 or '',
            'city': address.city,
            'state': address.state or '',
            'zip_code': address.zip_code,
            'country': address.country
        }
    })

@admin_bp.route('/lanyards/batch-update', methods=['POST'])
@login_required
def update_lanyard_status_batch():
    """Batch update lanyard fulfillment status for multiple users"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    # Get the batch update data from the request
    data = request.json
    if not data or 'updates' not in data or not isinstance(data['updates'], list):
        return jsonify({'success': False, 'message': 'Invalid request format'}), 400
    
    updates = data['updates']
    if not updates:
        return jsonify({'success': True, 'message': 'No updates to process', 'results': []}), 200
    
    # Track the results for each user update
    results = []
    sent_count = 0
    
    # Process each update
    for update in updates:
        try:
            user_id = update.get('userId')
            status = update.get('status')
            
            if user_id is None or status is None:
                results.append({'success': False, 'userId': user_id, 'message': 'Missing required fields'})
                continue
                
            user = User.query.get(user_id)
            if not user:
                results.append({'success': False, 'userId': user_id, 'message': 'User not found'})
                continue
            
            # Update the lanyard status
            user.lanyard_sent = status
            
            # If marking as sent, record the timestamp
            if status:
                user.lanyard_sent_date = datetime.utcnow()
                sent_count += 1
            else:
                user.lanyard_sent_date = None
            
            # Find user's first tournament (if any)
            first_tournament = None
            user_tourneys = UserTournament.query.filter_by(
                user_id=user.id,
                attending=True
            ).join(Tournament).order_by(Tournament.start_date).first()
            
            if user_tourneys:
                first_tournament = Tournament.query.get(user_tourneys.tournament_id)
            
            # Log the event
            from services.event_logger import log_event
            log_event('lanyard_marked_sent' if status else 'lanyard_marked_unsent', data={
                "target_user_id": user_id,
                "target_user_email": user.email,
                "admin_user": current_user.email,
                "tournament_id": first_tournament.id if first_tournament else None,
                "tournament_name": first_tournament.name if first_tournament else None,
                "ip": request.remote_addr,
                "timestamp": datetime.utcnow().isoformat(),
                "batch_update": True
            })
            
            # Add to results
            results.append({
                'success': True,
                'userId': user_id,
                'status': status
            })
            
        except Exception as e:
            results.append({
                'success': False,
                'userId': update.get('userId'),
                'message': str(e)
            })
    
    # Commit all changes at once
    try:
        db.session.commit()
        
        # Log the batch update event
        from services.event_logger import log_event
        log_event('lanyard_batch_update', data={
            'total_updates': len(updates),
            'successful_updates': sum(1 for r in results if r.get('success')),
            'sent_count': sent_count,
            'timestamp': datetime.utcnow().isoformat(),
            'admin_user': current_user.email,
            'ip': request.remote_addr
        })
        
        return jsonify({
            'success': True,
            'message': f'Successfully processed {len(results)} lanyard status updates',
            'results': results
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Database error: {str(e)}',
            'results': results
        }), 500

@admin_bp.route('/lanyards/update-note/<int:user_id>', methods=['POST'])
@login_required
def update_lanyard_note(user_id):
    """Update internal note for a user's lanyard order"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    note = request.form.get('note', '')
    
    # Add internal note field to the user if it doesn't exist yet
    if not hasattr(user, 'internal_note'):
        # For first usage, we'll store it in the user's event_data field
        # as a temporary solution until the model is updated
        event = Event()
        event.user_id = current_user.id
        event.name = "lanyard_note"
        event.event_data = {
            "target_user_id": user_id,
            "note": note,
            "timestamp": datetime.utcnow().isoformat()
        }
        db.session.add(event)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Stored in event log temporarily'})
    
    # If the model has been updated with the field, use it directly
    user.internal_note = note
    db.session.commit()
    
    # Log the event
    event = Event()
    event.user_id = current_user.id
    event.name = "lanyard_note_update"
    event.event_data = {
        "target_user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    db.session.add(event)
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/export-lanyards')
@login_required
def export_lanyards():
    """Export lanyard orders to CSV"""
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Get all users who ordered lanyards
    users_with_lanyards = User.query.filter_by(lanyard_ordered=True).all()
    
    if not users_with_lanyards:
        flash("No lanyard orders found.", "info")
        return redirect(url_for("admin.lanyard_fulfillment"))
    
    # Prepare CSV data
    csv_data = []
    headers = ["Name", "Email", "Full Address", "City", "State", "Zip", "Country", "First Tournament", "Other Tournaments", "Sessions", "Lanyard Sent", "Sent Date", "Internal Note"]
    
    for user in users_with_lanyards:
        # Get shipping address if available
        full_address = "Not provided"
        city = ""
        state = ""
        zip_code = ""
        country = ""
        
        address = ShippingAddress.query.filter_by(user_id=user.id).first()
        if address:
            address_parts = [
                address.name,
                address.address1
            ]
            if address.address2:
                address_parts.append(address.address2)
            
            full_address = ", ".join(address_parts)
            city = address.city
            state = address.state or ""
            zip_code = address.zip_code
            country = address.country
        
        # Get first tournament the user is attending
        first_tournament_str = "None"
        sessions_str = "None"
        other_tournaments_str = "None"
        
        user_tourneys = UserTournament.query.filter_by(
            user_id=user.id,
            attending=True
        ).join(Tournament).order_by(Tournament.start_date).all()
        
        if user_tourneys:
            # First tournament
            first_tourney = user_tourneys[0]
            tournament = Tournament.query.get(first_tourney.tournament_id)
            if tournament:
                first_tournament_str = f"{tournament.name} ({tournament.start_date.strftime('%b %d, %Y')})"
                sessions_str = first_tourney.session_label or "No sessions selected"
            
            # Other tournaments
            if len(user_tourneys) > 1:
                other_names = []
                for i in range(1, len(user_tourneys)):
                    t = Tournament.query.get(user_tourneys[i].tournament_id)
                    if t:
                        other_names.append(t.name)
                
                if other_names:
                    other_tournaments_str = ", ".join(other_names)
        
        # Try to get internal note if available
        internal_note = ""
        if hasattr(user, 'internal_note'):
            internal_note = user.internal_note or ""
        else:
            # Check if note exists in event data
            note_event = Event.query.filter_by(
                name="lanyard_note"
            ).filter(
                Event.event_data.contains(f'"target_user_id": {user.id}')
            ).order_by(Event.timestamp.desc()).first()
            
            if note_event and 'note' in note_event.event_data:
                internal_note = note_event.event_data.get('note', '')
        
        row = [
            user.get_full_name(),
            user.email,
            full_address,
            city,
            state,
            zip_code,
            country,
            first_tournament_str,
            other_tournaments_str,
            sessions_str,
            "Yes" if user.lanyard_sent else "No",
            user.lanyard_sent_date.strftime('%b %d, %Y') if user.lanyard_sent_date else "Not sent",
            internal_note
        ]
        
        csv_data.append(row)
    
    # Generate CSV response
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(csv_data)
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=lanyard_fulfillment.csv"
    response.headers["Content-type"] = "text/csv"
    
    # Log the export event
    event = Event()
    event.user_id = current_user.id
    event.name = "lanyard_export"
    event.event_data = {
        "exported_count": len(users_with_lanyards),
        "timestamp": datetime.utcnow().isoformat()
    }
    db.session.add(event)
    db.session.commit()
    
    return response