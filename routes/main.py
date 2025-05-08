
from flask import Blueprint, render_template 
from models import Tournament
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def homepage():
    tournaments = Tournament.query.order_by(Tournament.start_date).all()
    return render_template("homepage.html", tournaments=tournaments)
