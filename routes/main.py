from flask import Blueprint, render_template, abort, redirect, url_for, request, Response
from models import Tournament, User, UserTournament, BlogPost
import datetime
import re
from services.event_logger import log_event

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def public_home():
    from sqlalchemy import func
    from models import UserTournament
    
    # Get upcoming tournaments for the homepage showcase
    upcoming_tournaments = Tournament.query.filter(
        Tournament.start_date >= datetime.date.today()
    ).order_by(Tournament.start_date).limit(3).all()
    
    # Get attendance counts for each tournament
    tournaments_with_data = []
    for tournament in upcoming_tournaments:
        count = UserTournament.query.filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.attending == True,
            UserTournament.session_label.isnot(None)
        ).count()
        
        tournaments_with_data.append({
            'tournament': tournament,
            'attending_count': count
        })
    
    return render_template('public/home.html', 
                         tournaments_data=tournaments_with_data,
                         featured_tournaments=tournaments_with_data)

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
    from sqlalchemy import func
    from models import UserTournament
    
    # Get all future tournaments ordered by start date
    tournaments = Tournament.query.filter(
        Tournament.start_date >= datetime.date.today()
    ).order_by(Tournament.start_date).all()
    
    # Get attendance counts for each tournament
    attendance_counts = {}
    maybe_counts = {}
    for tournament in tournaments:
        # Count users definitely attending
        attending_count = UserTournament.query.filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.attending == True,
            UserTournament.session_label.isnot(None),
            UserTournament.session_label != ''
        ).count()
        attendance_counts[tournament.id] = attending_count
        
        # Count users who marked "maybe"
        maybe_count = UserTournament.query.filter(
            UserTournament.tournament_id == tournament.id,
            UserTournament.attendance_type == 'maybe'
        ).count()
        maybe_counts[tournament.id] = maybe_count
    
    return render_template('public/tournaments.html', 
                         tournaments=tournaments, 
                         attendance_counts=attendance_counts,
                         maybe_counts=maybe_counts)

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
    
    # Public version for anonymous users
    attending_count = UserTournament.query.filter_by(
        tournament_id=tournament.id, attending=True
    ).count()

    meeting_count = UserTournament.query.filter_by(
        tournament_id=tournament.id, attending=True, wants_to_meet=True
    ).count()

    all_sessions = UserTournament.query.with_entities(UserTournament.session_label).filter_by(
        tournament_id=tournament.id, attending=True
    ).all()

    from collections import Counter
    session_counts = Counter()
    for entry in all_sessions:
        if entry.session_label:
            session_counts.update(entry.session_label.split(','))

    most_popular_session = session_counts.most_common(1)[0][0] if session_counts else None

    # Get related blog posts
    blog_posts = BlogPost.query.filter_by(published=True).all()
    related_blog_posts = []
    for post in blog_posts:
        # Check for tournament name or slug in title and content (case insensitive)
        search_text = f"{post.title} {post.content}".lower()
        tournament_name_lower = tournament.name.lower()
        tournament_slug_lower = tournament.slug.lower()
        
        if tournament_name_lower in search_text or tournament_slug_lower in search_text:
            related_blog_posts.append(post)

    return render_template(
        'public/tournament_detail.html',
        tournament=tournament,
        attending_count=attending_count,
        meeting_count=meeting_count,
        most_popular_session=most_popular_session,
        related_blog_posts=related_blog_posts
    )

@main_bp.route('/how-it-works')
def how_it_works():
    return render_template('public/how_it_works.html',
                         page_title="How CourtSide Club Works - Tennis Fan Community",
                         page_description="Learn how CourtSide Club helps tennis fans connect at tournaments. Find other fans, get your lanyard, and join the community.")

@main_bp.route('/public-lanyard')
def lanyard_info():
    return render_template('public/lanyard.html')
    
@main_bp.route('/lanyard-info')
def lanyard_info_public():
    return render_template('public/lanyard_info.html')

@main_bp.route('/faqs')
def faqs():
    return render_template('public/faqs.html')

@main_bp.route('/about')
def about():
    return render_template('public/about.html')

@main_bp.route('/community')
def community():
    return render_template('public/community.html')



@main_bp.route('/blog')
def blog():
    # Get all published blog posts
    blog_posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).all()
    return render_template('public/blog.html', blog_posts=blog_posts)

@main_bp.route('/blog/<slug>')
def blog_post(slug):
    blog = BlogPost.query.filter_by(slug=slug, published=True).first_or_404()
    tournaments = Tournament.query.all()

    matched_tournaments = []
    content_to_check = f"{blog.title} {blog.content}"

    for t in tournaments:
        if re.search(rf"\b{re.escape(t.name)}\b", content_to_check, re.IGNORECASE) or \
           re.search(rf"\b{re.escape(t.slug)}\b", content_to_check, re.IGNORECASE):
            matched_tournaments.append(t)

    blog.related_tournaments = matched_tournaments

    return render_template('public/blog_post.html', blog=blog)

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
            url_for('main.lanyard_info_public', _external=True),
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
            url_for('main.lanyard_info_public', _external=True),
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

