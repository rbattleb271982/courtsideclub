from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Tournament

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

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