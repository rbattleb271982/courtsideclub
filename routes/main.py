
from flask import Blueprint, render_template, abort
from models import Tournament

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def public_home():
    return render_template('public/home.html')

@main_bp.route('/tournaments')
def public_tournaments():
    tournaments = Tournament.query.order_by(Tournament.start_date).all()
    return render_template('public/tournaments.html', tournaments=tournaments)

@main_bp.route('/tournaments/<slug>')
def public_tournament_detail(slug):
    tournament = Tournament.query.filter_by(slug=slug).first()
    if not tournament:
        abort(404)
    return render_template('public/tournament_detail.html', tournament=tournament)

@main_bp.route('/how-it-works')
def how_it_works():
    return render_template('public/how_it_works.html')

@main_bp.route('/lanyard')
def lanyard_info():
    return render_template('public/lanyard.html')

@main_bp.route('/faqs')
def faqs():
    return render_template('public/faqs.html')

@main_bp.route('/about')
def about():
    return render_template('public/about.html')

@main_bp.route('/blog')
def blog():
    return render_template('public/blog.html')

@main_bp.route('/privacy-policy')
def privacy():
    return render_template('public/privacy.html')

@main_bp.route('/terms')
def terms():
    return render_template('public/terms.html')
