from flask import Blueprint, render_template, abort, redirect, url_for, request, Response
from models import Tournament, User, UserTournament
import datetime
from services.event_logger import log_event

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def public_home():
    # Get next upcoming tournament for preview section
    next_tournament = Tournament.query.filter(
        Tournament.start_date >= datetime.date.today()
    ).order_by(Tournament.start_date).first()
    
    return render_template('public/home.html', next_tournament=next_tournament)

@main_bp.route('/invite')
def track_invite_click():
    """Track invite link clicks and redirect to homepage"""
    try:
        # Log the invite click event (no user ID needed for privacy)
        log_event(None, 'invite_link_clicked', {
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'referrer': request.headers.get('Referer', 'Unknown')
        })
    except Exception as e:
        # Don't break the redirect if logging fails
        print(f"Failed to log invite click: {e}")
    
    # Redirect to homepage
    return redirect(url_for('main.public_home'))

@main_bp.route('/tournaments')
def public_tournaments():
    tournament = Tournament.query.filter_by(slug='roland-garros').first()
    if not tournament:
        return render_template('public/tournaments.html', tournaments=[])
    return render_template('public/tournaments.html', tournaments=[tournament])

@main_bp.route('/tournaments/<slug>')
def public_tournament_detail(slug):
    from flask_login import current_user
    
    tournament = Tournament.query.filter_by(slug=slug).first_or_404()
    
    if current_user.is_authenticated:
        # Get user's tournament registration if logged in
        user_tournament = UserTournament.query.filter_by(
            user_id=current_user.id,
            tournament_id=tournament.id
        ).first()
        
        # Get tournament stats
        stats = {
            'attending': UserTournament.query.filter_by(tournament_id=tournament.id, attending=True).count(),
            'meetup': UserTournament.query.filter_by(tournament_id=tournament.id, attending=True, wants_to_meet=True).count(),
            'lanyards': UserTournament.query.filter_by(tournament_id=tournament.id, attending=True).join(User).filter_by(lanyard_ordered=True).count()
        }
        
        return render_template('tournament_detail.html',
                            tournament=tournament,
                            user_tournament=user_tournament,
                            stats=stats)
    
    # Show limited info for non-logged in users
    return render_template('public/tournament_detail.html', 
                         tournament=tournament)

@main_bp.route('/how-it-works')
def how_it_works():
    return render_template('public/how_it_works.html',
                         page_title="How CourtSide Club Works - Tennis Fan Community",
                         page_description="Learn how CourtSide Club helps tennis fans connect at tournaments. Find other fans, get your lanyard, and join the community.")

@main_bp.route('/lanyard')
def lanyard_info():
    return render_template('public/lanyard.html')
    
@main_bp.route('/lanyard-info')
def lanyard_info_public():
    return render_template('public/lanyard_info.html')

@main_bp.route('/faqs')
def faqs():
    return render_template('public/faqs.html')

# About page content has been moved to the homepage
# @main_bp.route('/about')
# def about():
#     return render_template('public/about.html')

# Blog route removed

@main_bp.route('/privacy-policy')
def privacy():
    return render_template('public/privacy.html')

@main_bp.route('/terms')
def terms():
    return render_template('public/terms.html')

@main_bp.route('/robots.txt')
def robots():
    host = request.host_url
    robot_text = f"""User-agent: *
Disallow:

Sitemap: {host}sitemap.xml
"""
    return Response(robot_text, mimetype='text/plain')

@main_bp.route('/sitemap.xml')
def sitemap():
    try:
        # Get all public tournaments for the sitemap
        tournaments = Tournament.query.all()
        
        # Basic pages
        pages = [
            url_for('main.public_home', _external=True),
            url_for('main.how_it_works', _external=True),
            url_for('main.lanyard_info', _external=True),
            url_for('main.faqs', _external=True),
            url_for('main.blog', _external=True),
            url_for('main.privacy', _external=True),
            url_for('main.terms', _external=True),
        ]
        
        # Add all tournament detail pages
        for tournament in tournaments:
            pages.append(url_for('main.public_tournament_detail', slug=tournament.slug, _external=True))
    except Exception as e:
        # Fallback to basic pages if database is unavailable
        pages = [
            url_for('main.public_home', _external=True),
            url_for('main.how_it_works', _external=True),
            url_for('main.lanyard_info', _external=True),
            url_for('main.faqs', _external=True),
            url_for('main.blog', _external=True),
            url_for('main.privacy', _external=True),
            url_for('main.terms', _external=True),
        ]
        
    # Build the XML sitemap with proper formatting
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for page in pages:
        xml += '  <url>\n'
        xml += f'    <loc>{page}</loc>\n'
        xml += '    <changefreq>weekly</changefreq>\n'
        xml += '  </url>\n'
    
    xml += '</urlset>'
    return Response(xml, mimetype='application/xml')