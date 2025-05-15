from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Tournament, UserTournament, User

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
        registrations = UserTournament.query.filter_by(tournament_id=t.id).all()
        total_attending = sum(1 for r in registrations if r.attending)
        total_meetups = sum(1 for r in registrations if r.wants_to_meet)
        
        dashboard_data.append({
            "tournament": t,
            "total_attending": total_attending,
            "total_meetups": total_meetups
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
import csv
from io import StringIO
from flask import Response

@admin_bp.route('/admin/export-lanyards')
@login_required
def export_lanyards():
    if not current_user.is_admin:
        return "Access denied", 403

    from models import User, UserTournament, Tournament

    user_data = (
        db.session.query(User, UserTournament, Tournament)
        .join(UserTournament, User.id == UserTournament.user_id)
        .join(Tournament, Tournament.id == UserTournament.tournament_id)
        .filter(User.lanyard_ordered == True)
        .filter(UserTournament.wants_to_meet == True)
        .order_by(Tournament.start_date)
        .all()
    )

    # Generate CSV
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["User Name", "Email", "Tournament", "Session", "City", "Country", "Start Date"])

    for user, ut, tournament in user_data:
        writer.writerow([
            user.name or f"{user.first_name} {user.last_name}",
            user.email,
            tournament.name,
            ut.session_label or "—",
            tournament.city,
            tournament.country,
            tournament.start_date.strftime("%Y-%m-%d")
        ])

    return Response(
        csv_buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=lanyard_orders.csv"}
    )
