from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Tournament, UserTournament, User, Event

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.homepage"))

    tournaments = Tournament.query.order_by(Tournament.start_date).all()
    dashboard_data = []
    
    for t in tournaments:
        registrations = db.session.query(UserTournament).filter_by(tournament_id=t.id).all()

        session_counts = {}
        for reg in registrations:
            sessions = (reg.session_label or "").split(", ")
            for session in sessions:
                if session:
                    session_counts[session] = session_counts.get(session, 0) + 1

        total_attending = len(registrations)
        total_meetups = sum(1 for r in registrations if r.wants_to_meet)

        dashboard_data.append({
            "tournament": t,
            "total_attending": total_attending,
            "total_meetups": total_meetups,
            "session_counts": session_counts
        })

    return render_template("admin_dashboard.html", dashboard_data=dashboard_data)

@admin_bp.route('/tournament/<tournament_slug>/attendees')
@login_required
def view_attendees(tournament_slug):
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.homepage"))

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
        return redirect(url_for("main.homepage"))

    tournaments = Tournament.query.order_by(Tournament.start_date).all()
    return render_template("admin_tournament_list.html", tournaments=tournaments)

@admin_bp.route("/tournaments/<tournament_id>/edit", methods=["GET", "POST"])
@login_required
def edit_tournament(tournament_id):
    """Admin view to edit tournament details"""
    if not getattr(current_user, "is_admin", False):
        flash("Access denied.", "danger")
        return redirect(url_for("main.homepage"))

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
        return redirect(url_for("main.homepage"))
        
    events = Event.query.order_by(Event.timestamp.desc()).limit(100).all()
    return render_template("admin_events.html", events=events)

@admin_bp.route('/event-types')
@login_required
def view_event_types():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.homepage"))
        
    event_names = db.session.query(Event.name).distinct().all()
    event_names = sorted([name[0] for name in event_names])
    return render_template("admin_event_types.html", event_names=event_names)

import csv
from io import StringIO
from flask import Response

from flask import Response
from io import StringIO
import csv

@admin_bp.route('/export-lanyards')
@login_required
def export_lanyards():
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.homepage"))

    # Get users who submitted a shipping address AND selected a session
    results = (
        db.session.query(User, ShippingAddress)
        .join(ShippingAddress, User.id == ShippingAddress.user_id)
        .join(UserTournament, User.id == UserTournament.user_id)
        .distinct(User.id)
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Address1', 'Address2', 'City', 'State', 'Zip', 'Country', 'Email'])

    for user, address in results:
        writer.writerow([
            address.name,
            address.address1,
            address.address2 or '',
            address.city,
            address.state,
            address.zip_code,
            address.country,
            user.email
        ])

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=lanyard_orders.csv"})
