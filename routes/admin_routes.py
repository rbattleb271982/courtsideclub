from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify, make_response
from flask_login import login_required, current_user
from models import db, Tournament, UserTournament, User, Event, ShippingAddress
from sqlalchemy import func, desc
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
            
            # Prepare data for the dashboard
            dashboard_data.append({
                'tournament': tournament,
                'total_registrations': total_registrations,
                'attending_count': attending_count,
                'open_to_meet_count': open_to_meet_count,
                'day_count': day_count,
                'night_count': night_count,
                'start_date_unix': tournament.start_date.timestamp() if tournament.start_date else 0
            })

        # Sort tournaments by start date
        dashboard_data.sort(key=lambda x: x['start_date_unix'])
        
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
                
                if session_key not in session_stats:
                    session_stats[session_key] = {'Day': 0, 'Night': 0, 'Total': 0}
                    
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
        tournament.about = request.form.get('about', '')
        
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
        tournament.surface = request.form.get('surface', '')
        
        db.session.commit()
        
        # Log the event
        event = Event()
        event.user_id = current_user.id
        event.name = "tournament_edit"
        event.event_data = {
            "tournament_id": tournament.id,
            "tournament_name": tournament.name,
            "fields_updated": ["about", "draw_url", "schedule_url", "surface"]
        }
        db.session.add(event)
        db.session.commit()
        
        flash(f"Tournament '{tournament.name}' has been updated.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating tournament: {str(e)}", "danger")
    
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
            Event.date_created.between(start_datetime, end_datetime)
        ).order_by(Event.date_created.desc()).all()
        
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
        "past_tournament_remove": "Removed past tournament",
        "lanyard_fulfillment_update": "Updated lanyard shipping status"
    }
    
    # Get event counts per type
    event_counts = db.session.query(
        Event.name, 
        func.count(Event.id).label('count')
    ).filter(
        Event.date_created.between(start_datetime, end_datetime)
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
    
    # Get daily event counts for chart
    daily_counts = db.session.query(
        func.date(Event.date_created).label('date'),
        func.count(Event.id).label('count')
    ).filter(
        Event.date_created.between(start_datetime, end_datetime)
    ).group_by('date').order_by('date').all()
    
    # Prepare chart data
    dates = []
    counts = []
    for date, count in daily_counts:
        dates.append(date.strftime('%Y-%m-%d'))
        counts.append(count)
    
    # Get user counts for chart
    user_event_counts = db.session.query(
        User.email,
        func.count(Event.id).label('count')
    ).join(Event, User.id == Event.user_id).filter(
        Event.date_created.between(start_datetime, end_datetime)
    ).group_by(User.email).order_by(desc('count')).limit(10).all()
    
    # Prepare user data
    user_emails = []
    user_counts = []
    for email, count in user_event_counts:
        user_emails.append(email)
        user_counts.append(count)
    
    return render_template(
        'admin_event_summary.html',
        event_data=event_data,
        start_date=start_date,
        end_date=end_date,
        prev_start=prev_start,
        prev_end=prev_end,
        next_start=next_start,
        next_end=next_end,
        dates=dates,
        counts=counts,
        user_emails=user_emails,
        user_counts=user_counts
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
        Event.date_created,
        User.email
    ).join(User, User.id == Event.user_id).filter(
        Event.date_created.between(start_datetime, end_datetime)
    ).order_by(Event.date_created.desc()).all()
    
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
    
    for user in users_with_lanyards:
        # Get shipping address if available
        has_address = bool(ShippingAddress.query.filter_by(user_id=user.id).first())
        
        # Get first tournament the user is attending
        first_tournament = None
        first_tournament_date = None
        sessions = None
        
        user_tourneys = UserTournament.query.filter_by(
            user_id=user.id,
            attending=True
        ).join(Tournament).order_by(Tournament.start_date).all()
        
        if user_tourneys:
            first_tournament = Tournament.query.get(user_tourneys[0].tournament_id)
            if first_tournament:
                first_tournament_date = first_tournament.start_date
                sessions = user_tourneys[0].session_label
        
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
    
    return render_template(
        "admin_lanyard_fulfillment.html",
        lanyard_data=lanyard_data,
        total_ordered=total_ordered,
        total_sent=total_sent,
        total_not_sent=total_not_sent,
        next_tournament=next_tournament,
        unsent_next_tournament=unsent_next_tournament
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
    
    # Log the event
    event = Event()
    event.user_id = current_user.id
    event.name = "lanyard_fulfillment_update"
    event.event_data = {
        "target_user_id": user_id,
        "lanyard_sent": status,
        "timestamp": datetime.utcnow().isoformat()
    }
    db.session.add(event)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'sent': status,
        'date': user.lanyard_sent_date.strftime('%b %d, %Y %H:%M UTC') if user.lanyard_sent_date else None
    })

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
    headers = ["Name", "Email", "Address", "First Tournament", "Sessions", "Lanyard Sent", "Sent Date"]
    
    for user in users_with_lanyards:
        # Get shipping address if available
        shipping_address = ""
        address = ShippingAddress.query.filter_by(user_id=user.id).first()
        if address:
            shipping_address = f"{address.name}, {address.address1}, {address.address2 or ''}, {address.city}, {address.state or ''}, {address.zip_code}, {address.country}"
        
        # Get first tournament the user is attending
        first_tournament_str = "None"
        sessions_str = "None"
        
        user_tourneys = UserTournament.query.filter_by(
            user_id=user.id,
            attending=True
        ).join(Tournament).order_by(Tournament.start_date).all()
        
        if user_tourneys:
            first_tourney = user_tourneys[0]
            tournament = Tournament.query.get(first_tourney.tournament_id)
            if tournament:
                first_tournament_str = f"{tournament.name} ({tournament.start_date.strftime('%b %d, %Y')})"
                sessions_str = first_tourney.session_label or "No sessions selected"
        
        row = [
            user.get_full_name(),
            user.email,
            shipping_address or "Not provided",
            first_tournament_str,
            sessions_str,
            "Yes" if user.lanyard_sent else "No",
            user.lanyard_sent_date.strftime('%b %d, %Y %H:%M UTC') if user.lanyard_sent_date else "Not sent"
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
    event.event_data = {"exported_count": len(users_with_lanyards)}
    db.session.add(event)
    db.session.commit()
    
    return response