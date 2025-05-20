from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from models import db, Tournament, UserTournament, User, Event
from sqlalchemy import func, desc
import csv
from io import StringIO

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
        
        for t in tournaments:
            try:
                # Only count users who are marked as attending
                attending_registrations = db.session.query(UserTournament).filter_by(
                    tournament_id=t.id, 
                    attending=True
                ).all()

                # Count session attendance
                session_counts = {}
                for reg in attending_registrations:
                    sessions = (reg.session_label or "").split(", ")
                    for session in sessions:
                        if session:
                            session_counts[session] = session_counts.get(session, 0) + 1

                # Total attending users
                total_attending = len(attending_registrations)
                
                # Count users who want to meet
                total_meetups = sum(1 for r in attending_registrations if r.wants_to_meet)
                
                # Count lanyard orders safely
                try:
                    lanyard_count = db.session.query(UserTournament).filter_by(
                        tournament_id=t.id,
                        attending=True
                    ).join(User).filter_by(lanyard_ordered=True).count()
                except Exception as e:
                    # Fallback if the join query fails
                    lanyard_count = 0
                    print(f"Error counting lanyards for tournament {t.id}: {str(e)}")

                dashboard_data.append({
                    "tournament": t,
                    "total_attending": total_attending,
                    "total_meetups": total_meetups,
                    "total_lanyards": lanyard_count,
                    "session_counts": session_counts
                })
            except Exception as tournament_error:
                # Skip this tournament if there's an error
                print(f"Error processing tournament {t.id}: {str(tournament_error)}")
                continue
                
    except Exception as e:
        # Handle database connection errors
        flash(f"Error accessing dashboard data. Please try again later.", "danger")
        print(f"Dashboard error: {str(e)}")
        return render_template("admin_dashboard.html", dashboard_data=[])

    return render_template("admin_dashboard.html", dashboard_data=dashboard_data)

@admin_bp.route('/tournaments/<tournament_slug>')
@login_required
def view_tournament(tournament_slug):
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))

    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
    
    # Get all attending users for this tournament
    user_tourneys = UserTournament.query.filter_by(
        tournament_id=tournament.id,
        attending=True
    ).all()
    
    # Build session attendance data
    session_counts = {}
    total_attending = len(user_tourneys)
    
    for registration in user_tourneys:
        sessions = (registration.session_label or "").split(", ")
        for session in sessions:
            if session:
                session_counts[session] = session_counts.get(session, 0) + 1
    
    # Sort sessions by attendance count (highest first)
    sorted_sessions = sorted(
        [{"label": label, "count": count} for label, count in session_counts.items()],
        key=lambda x: x["count"],
        reverse=True
    )
    
    return render_template(
        "admin_tournament_detail.html",
        tournament=tournament,
        total_attending=total_attending,
        sessions=sorted_sessions
    )

@admin_bp.route('/tournament/<tournament_slug>/attendees')
@login_required
def view_attendees(tournament_slug):
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))

    tournament = Tournament.query.filter_by(slug=tournament_slug).first_or_404()
    user_tourneys = UserTournament.query.filter_by(
        tournament_id=tournament.id,
        attending=True
    ).all()

    return render_template(
        "admin_attendees.html",
        tournament=tournament,
        user_tourneys=user_tourneys
    )

@admin_bp.route("/tournaments", methods=["GET", "POST"])
@login_required
def list_tournaments():
    """Admin view to list all tournaments for editing"""
    if not getattr(current_user, "is_admin", False):
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))

    # Handle POST request for creating new tournament
    if request.method == "POST":
        try:
            # Extract form data
            tournament_id = request.form.get("id", "").strip().lower()
            name = request.form.get("name", "").strip()
            start_date = request.form.get("start_date")
            end_date = request.form.get("end_date")
            city = request.form.get("city", "").strip()
            country = request.form.get("country", "").strip()
            event_type = request.form.get("event_type")
            tour_type = request.form.get("tour_type")
            surface = request.form.get("surface")
            draw_url = request.form.get("draw_url", "")
            schedule_url = request.form.get("schedule_url", "")
            
            # Validate required fields
            if not all([tournament_id, name, start_date, end_date, city, country, event_type, tour_type]):
                flash("Please fill in all required fields.", "danger")
                tournaments = Tournament.query.order_by(Tournament.start_date).all()
                return render_template("admin_tournament_list.html", tournaments=tournaments)
            
            # Create slug from tournament name
            slug = tournament_id.replace(" ", "_").lower()
            
            # Check if tournament ID already exists
            existing = Tournament.query.filter_by(id=tournament_id).first()
            if existing:
                flash(f"A tournament with ID '{tournament_id}' already exists.", "danger")
                tournaments = Tournament.query.order_by(Tournament.start_date).all()
                return render_template("admin_tournament_list.html", tournaments=tournaments)
            
            # Create new tournament and set its attributes
            tournament = Tournament()
            tournament.id = tournament_id
            tournament.slug = slug
            tournament.name = name
            tournament.start_date = start_date
            tournament.end_date = end_date
            tournament.city = city
            tournament.country = country
            tournament.event_type = event_type
            tournament.tour_type = tour_type
            tournament.surface = surface
            tournament.draw_url = draw_url
            tournament.schedule_url = schedule_url
            tournament.sessions = []  # Empty sessions array
            
            db.session.add(tournament)
            db.session.commit()
            
            flash(f"Tournament '{name}' added successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding tournament: {str(e)}", "danger")
    
    # GET request or after POST - show tournament list
    tournaments = Tournament.query.order_by(Tournament.start_date).all()
    return render_template("admin_tournament_list.html", tournaments=tournaments)

@admin_bp.route("/tournaments/<tournament_id>/edit", methods=["GET", "POST"])
@login_required
def edit_tournament(tournament_id):
    """Admin view to edit tournament details"""
    if not getattr(current_user, "is_admin", False):
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))

    tournament = Tournament.query.get_or_404(tournament_id)

    if request.method == "POST":
        tournament.about = request.form.get("about", "")
        tournament.draw_url = request.form.get("draw_url", "")
        tournament.schedule_url = request.form.get("schedule_url", "")
        db.session.commit()
        flash("Tournament updated successfully.", "success")
        return redirect(url_for("admin.edit_tournament", tournament_id=tournament.id))

    return render_template("admin_edit_tournament.html", tournament=tournament)
@admin_bp.route('/events')
@login_required
def view_events():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Handle event type filtering
    event_type = request.args.get('event_type')
    
    # Build the query
    events_query = Event.query.order_by(Event.timestamp.desc())
    
    # Apply filter if specified
    if event_type:
        events_query = events_query.filter(Event.name == event_type)
        
    # Get the results (limited to 100)
    events = events_query.limit(100).all()
    
    return render_template(
        "admin_events.html", 
        events=events, 
        event_type=event_type
    )

@admin_bp.route('/event-types')
@login_required
def view_event_types():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
        
    event_names = db.session.query(Event.name).distinct().all()
    event_names = sorted([name[0] for name in event_names])
    return render_template("admin_event_types.html", event_names=event_names)

@admin_bp.route('/event-summary')
@login_required
def event_summary():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Define a mapping dictionary for event descriptions
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
    
    # Get sorted event counts (most frequent first)
    event_counts = db.session.query(
        Event.name, 
        func.count(Event.id).label('count')
    ).group_by(Event.name).order_by(desc('count')).all()
    
    # Process the results with descriptions
    event_summary = []
    for event_name, count in event_counts:
        description = event_descriptions.get(event_name, "User action")
        event_summary.append({
            'name': event_name,
            'count': count,
            'description': description
        })
    
    # Get total events count
    total_events = sum(item['count'] for item in event_summary)
    
    # Determine sort direction
    sort_dir = request.args.get('sort_dir', 'desc')
    sort_by = request.args.get('sort_by', 'count')
    
    # Sort results based on parameters
    if sort_by == 'name':
        event_summary.sort(key=lambda x: x['name'], reverse=(sort_dir == 'desc'))
    elif sort_by == 'count':
        event_summary.sort(key=lambda x: x['count'], reverse=(sort_dir == 'desc'))
    elif sort_by == 'description':
        event_summary.sort(key=lambda x: x['description'], reverse=(sort_dir == 'desc'))
    
    return render_template(
        "admin_event_summary.html", 
        event_summary=event_summary,
        total_events=total_events,
        sort_by=sort_by,
        sort_dir=sort_dir
    )

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
    output = StringIO()
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

from models import ShippingAddress

@admin_bp.route('/export-lanyards')
@login_required
def export_lanyards():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))

    # Get users who meet these criteria:
    # 1. Have lanyard_ordered=True
    # 2. Are attending at least one tournament (UserTournament.attending=True)
    # 3. Have selected at least one session (UserTournament.session_label is not empty)
    # 4. Have a shipping address on file
    results = (
        db.session.query(User, ShippingAddress)
        .join(ShippingAddress, User.id == ShippingAddress.user_id)
        .join(UserTournament, User.id == UserTournament.user_id)
        .filter(
            User.lanyard_ordered == True,
            UserTournament.attending == True,
            UserTournament.session_label.isnot(None),
            UserTournament.session_label != ''
        )
        .distinct(User.id)
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Email', 'Address1', 'Address2', 'City', 'State', 'Zip', 'Country', 'Attending Tournaments'])

    for user, address in results:
        # Get all tournaments this user is attending
        attending_tournaments = (
            db.session.query(Tournament.name)
            .join(UserTournament, Tournament.id == UserTournament.tournament_id)
            .filter(
                UserTournament.user_id == user.id,
                UserTournament.attending == True
            )
            .all()
        )
        tournament_names = "; ".join([t[0] for t in attending_tournaments])
        
        writer.writerow([
            user.get_full_name(),
            user.email,
            address.address1,
            address.address2 or '',
            address.city,
            address.state or '',
            address.zip_code,
            address.country,
            tournament_names
        ])

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=lanyard_orders.csv"})
