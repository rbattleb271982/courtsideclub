from flask import Blueprint, render_template 
from models import Tournament
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def homepage():
    from datetime import datetime
    today = datetime.now().date()
    tournaments = Tournament.query.filter(Tournament.start_date >= today).order_by(Tournament.start_date).all()
    return render_template("homepage.html", tournaments=tournaments)

@main_bp.route("/ping")
def ping():
    return "✅ App is running"

@main_bp.route("/test-home")
def test_home():
    return render_template("homepage.html", tournaments=[])