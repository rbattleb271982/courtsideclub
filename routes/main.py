from flask import Blueprint, render_template, abort
from models import Tournament
import datetime

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def public_home():
    # Get next upcoming tournament for preview section
    next_tournament = Tournament.query.filter(
        Tournament.start_date >= datetime.date.today()
    ).order_by(Tournament.start_date).first()
    
    return render_template('public/home.html', next_tournament=next_tournament)

@main_bp.route('/tournaments')
def public_tournaments():
    tournaments = Tournament.query.filter(Tournament.start_date >= datetime.date.today()).order_by(Tournament.start_date).all()
    return render_template('public/tournaments.html', tournaments=tournaments)

@main_bp.route('/tournaments/<slug>')
def public_tournament_detail(slug):
    tournament = Tournament.query.filter_by(slug=slug).first()
    if not tournament:
        abort(404)
    return render_template('public/tournament_detail.html', tournament=tournament)

@main_bp.route('/how-it-works')
def how_it_works():
    return render_template('public/how_it_works.html',
                         page_title="How CourtSide Club Works - Tennis Fan Community",
                         page_description="Learn how CourtSide Club helps tennis fans connect at tournaments. Find other fans, get your lanyard, and join the community.")

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

@main_bp.route('/sitemap.xml')
def sitemap():
    from flask import Response, url_for
    pages = [
        url_for('main.public_home', _external=True),
        url_for('main.public_tournaments', _external=True),
        url_for('main.how_it_works', _external=True),
        url_for('main.lanyard_info', _external=True),
        url_for('main.faqs', _external=True),
        url_for('main.about', _external=True),
        url_for('main.blog', _external=True),
        url_for('main.privacy', _external=True),
        url_for('main.terms', _external=True),
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for page in pages:
        xml += f"<url><loc>{page}</loc></url>\n"
    xml += "</urlset>"
    return Response(xml, mimetype='application/xml')