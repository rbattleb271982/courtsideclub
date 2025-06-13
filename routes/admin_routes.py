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
            
            # Lanyard functionality discontinued - count set to 0
            lanyard_count = 0
            
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

@admin_bp.route('/admin/tournament/<tournament_slug>', methods=['GET'])
@login_required
def view_tournament(tournament_slug):
    print(f"DEBUG: ADMIN ROUTE CALLED for {tournament_slug}")
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
                    'wants_to_meet': wants_to_meet
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
                'wants_to_meet': wants_to_meet
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
        external_url_input = request.form.get('external_url', '').strip()
        if external_url_input:
            if not external_url_input.startswith('http'):
                tournament.external_url = f"https://{external_url_input}"
            else:
                tournament.external_url = external_url_input
        else:
            tournament.external_url = None
        
        draw_url_input = request.form.get('draw_url', '').strip()
        if draw_url_input:
            if not draw_url_input.startswith('http'):
                tournament.draw_url = f"https://{draw_url_input}"
            else:
                tournament.draw_url = draw_url_input
        else:
            tournament.draw_url = None
        
        bracket_url_input = request.form.get('bracket_url', '').strip()
        if bracket_url_input:
            if not bracket_url_input.startswith('http'):
                tournament.bracket_url = f"https://{bracket_url_input}"
            else:
                tournament.bracket_url = bracket_url_input
        else:
            tournament.bracket_url = None
        
        schedule_url_input = request.form.get('schedule_url', '').strip()
        if schedule_url_input:
            if not schedule_url_input.startswith('http'):
                tournament.schedule_url = f"https://{schedule_url_input}"
            else:
                tournament.schedule_url = schedule_url_input
        else:
            tournament.schedule_url = None
        
        # Update surface if provided
        surface = request.form.get('surface', '').strip()
        tournament.surface = surface if surface else None
        
        # Update commentary if provided
        commentary = request.form.get('commentary', '').strip()
        tournament.commentary = commentary if commentary else None
        
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
            
        log_event(current_user.id, 'admin_tournament_updated', data={
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
    
    # Core events to show by default
    core_event_names = [
        'user_signup', 'user_login', 'user_logout',
        'password_reset_requested', 'password_reset_successful',
        'email_opt_in_changed', 'profile_updated', 'profile_completed',
        'attend_tournament', 'unattend_tournament', 'tournament_attendance_status_changed', 
        'session_selected', 'session_unselected', 'tournament_session_update',
        'tournaments_added_to_profile', 'wants_to_meet_enabled', 'wants_to_meet_disabled',
        'tournament_page_viewed', 'tournament_filter_applied',
        'lanyard_order_eligible', 'lanyard_order_started', 'lanyard_order_abandoned',
        'lanyard_order_submitted', 'lanyard_export', 'lanyard_shipped',
        'tournament_created', 'tournament_edit', 'admin_tournament_updated',
        'admin_manual_user_update', 'admin_lanyard_override',
        'reminder_email_sent', 'meetup_email_sent', 'lanyard_reminder_sent',
        'email_send_failed', 'email_bounced', 'email_unsubscribed'
    ]

    # Optional/debug events to hide by default
    optional_event_names = [
        'detailed_event', 'example_event', 'test_event',
        'qa_simulated_user_action', 'debug_lanyard_gate_triggered',
        'homepage_visited', 'how_it_works_visited', 'about_page_viewed',
        'invite_sent'
    ]
    
    # Add any existing event descriptions not explicitly in either list to optional events
    for event_name in event_descriptions.keys():
        if event_name not in core_event_names and event_name not in optional_event_names:
            optional_event_names.append(event_name)
    
    # Get actual event counts from the database
    db_event_counts = db.session.query(
        Event.name, 
        func.count(Event.id).label('count')
    ).group_by(Event.name).all()
    
    # Convert query result to a dictionary for easier lookup
    count_dict = {event_name: count for event_name, count in db_event_counts}
    
    # Build stats for core events
    core_events = []
    total_core_events = 0
    
    for event_name in core_event_names:
        count = count_dict.get(event_name, 0)
        description = event_descriptions.get(event_name, "User action")
        total_core_events += count
        
        core_events.append({
            'name': event_name,
            'count': count,
            'description': description
        })
    
    # Build stats for optional events
    optional_events = []
    total_optional_events = 0
    
    for event_name in optional_event_names:
        count = count_dict.get(event_name, 0)
        description = event_descriptions.get(event_name, "User action")
        total_optional_events += count
        
        optional_events.append({
            'name': event_name,
            'count': count,
            'description': description
        })
        
    # Also include any events found in the database that aren't in our expected lists
    for event_name, count in count_dict.items():
        if event_name not in core_event_names and event_name not in optional_event_names:
            description = event_descriptions.get(event_name, "User action")
            total_optional_events += count
            
            optional_events.append({
                'name': event_name,
                'count': count,
                'description': description
            })
    
    # Get optional URL parameters
    sort_by = request.args.get('sort_by', 'count')
    sort_dir = request.args.get('sort_dir', 'desc')
    show_all = request.args.get('show_all') == '1'
    
    # Apply sorting to core events
    if sort_by == 'name':
        core_events = sorted(core_events, key=lambda x: x['name'].lower(), reverse=(sort_dir == 'desc'))
    elif sort_by == 'count':
        core_events = sorted(core_events, key=lambda x: x['count'], reverse=(sort_dir == 'desc'))
    elif sort_by == 'description':
        core_events = sorted(core_events, key=lambda x: x['description'].lower(), reverse=(sort_dir == 'desc'))
    
    # Apply sorting to optional events (if they will be shown)
    if show_all:
        if sort_by == 'name':
            optional_events = sorted(optional_events, key=lambda x: x['name'].lower(), reverse=(sort_dir == 'desc'))
        elif sort_by == 'count':
            optional_events = sorted(optional_events, key=lambda x: x['count'], reverse=(sort_dir == 'desc'))
        elif sort_by == 'description':
            optional_events = sorted(optional_events, key=lambda x: x['description'].lower(), reverse=(sort_dir == 'desc'))
    
    return render_template(
        'admin_event_summary.html',
        core_events=core_events,
        optional_events=optional_events,
        total_core_events=total_core_events,
        total_optional_events=total_optional_events,
        total_events=total_core_events + total_optional_events,
        show_all=show_all,
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

