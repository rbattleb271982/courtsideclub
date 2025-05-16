from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Tournament, UserTournament, User, Event

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))

    tournaments = Tournament.query.order_by(Tournament.start_date).all()
    dashboard_data = []
    
    for t in tournaments:
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
        
        # Count lanyard orders - users who are attending AND ordered a lanyard
        lanyard_count = db.session.query(UserTournament).filter_by(
            tournament_id=t.id,
            attending=True
        ).join(User).filter_by(lanyard_ordered=True).count()

        dashboard_data.append({
            "tournament": t,
            "total_attending": total_attending,
            "total_meetups": total_meetups,
            "total_lanyards": lanyard_count,
            "session_counts": session_counts
        })

    return render_template("admin_dashboard.html", dashboard_data=dashboard_data)

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

@admin_bp.route("/tournaments")
@login_required
def list_tournaments():
    """Admin view to list all tournaments for editing"""
    if not getattr(current_user, "is_admin", False):
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))

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
        
    events = Event.query.order_by(Event.timestamp.desc()).limit(100).all()
    return render_template("admin_events.html", events=events)

@admin_bp.route('/event-types')
@login_required
def view_event_types():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
        
    event_names = db.session.query(Event.name).distinct().all()
    event_names = sorted([name[0] for name in event_names])
    return render_template("admin_event_types.html", event_names=event_names)

import csv
from io import StringIO
from flask import Response
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
