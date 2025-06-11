from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from agents.email_reminder import run_email_reminder
from agents.lanyard_reminder import run_lanyard_reminder_agent as run_lanyard_agent
from agents.post_event_followup import run_post_event_followup_agent
from agents.pre_tournament_reminder import run_pre_tournament_reminder_agent
from models import Tournament
from datetime import datetime, timedelta
from openai import OpenAI
import logging
import json
import os

logger = logging.getLogger(__name__)

admin_agents_bp = Blueprint('admin_agents', __name__, url_prefix='/admin/agents')

@admin_agents_bp.before_request
@login_required
def require_admin():
    """Ensure only admin users can access agent controls"""
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
        flash('Admin access required.', 'error')
        return redirect(url_for('main.public_home'))

@admin_agents_bp.route('/')
def agents_dashboard():
    """Main AI agents control panel"""
    return render_template('admin/agents.html')

@admin_agents_bp.route('/overview')
def agents_overview():
    """Agent architecture overview with visual diagram and comprehensive agent list"""
    return render_template('admin/agents_overview.html')

@admin_agents_bp.route('/run/email_reminder', methods=['POST'])
def run_email_reminder_agent():
    """Execute the email reminder agent manually"""
    try:
        preview = request.form.get('preview_mode') == 'on'
        logger.info(f"Admin {current_user.email} triggered email reminder agent (preview: {preview})")
        
        # Set a timeout for the entire operation
        import signal
        
        def agent_timeout_handler(signum, frame):
            raise TimeoutError("Agent execution timeout")
        
        signal.signal(signal.SIGALRM, agent_timeout_handler)
        signal.alarm(60)  # 60 second timeout for entire operation
        
        try:
            # Run the email reminder agent
            result = run_email_reminder(preview=preview)
            signal.alarm(0)  # Cancel timeout
            
            if result and result.get('status') == 'success':
                emails_sent = result.get('emails_sent', 0)
                tournaments_processed = result.get('tournaments_processed', 0)
                
                if preview:
                    flash(f"✅ Email Reminder Agent preview completed — would have sent {emails_sent} emails for {tournaments_processed} tournament(s)", 'info')
                else:
                    emails_count = int(emails_sent) if emails_sent else 0
                    if emails_count > 0:
                        import datetime
                        now = datetime.datetime.now()
                        time_str = now.strftime("%B %d at %I:%M%p").lower()
                        flash(f"✅ Email Reminder Agent ran successfully on {time_str} — {emails_count} users emailed", 'success')
                    else:
                        flash(f"✅ Email Reminder Agent completed — no emails needed at this time", 'info')
            else:
                error_msg = result.get('message', 'Unknown error') if result else 'Agent returned no result'
                flash(f"❌ Email Reminder Agent failed: {error_msg}", 'danger')
        except TimeoutError:
            signal.alarm(0)
            flash("❌ Email Reminder Agent timed out — operation took too long", 'danger')
        finally:
            signal.alarm(0)  # Ensure timeout is cancelled
            
    except Exception as e:
        logger.error(f"Error running email reminder agent: {str(e)}", exc_info=True)
        flash(f"❌ Error running Email Reminder Agent: Check logs for details", 'danger')
    
    return redirect(url_for('admin_agents.agents_dashboard'))

@admin_agents_bp.route('/run/tournament_summary', methods=['POST'])
def run_tournament_summary_agent():
    """Execute the tournament summary agent manually"""
    try:
        logger.info(f"Admin {current_user.email} triggered tournament summary agent")
        
        # Set a timeout for the entire operation
        import signal
        
        def agent_timeout_handler(signum, frame):
            raise TimeoutError("Agent execution timeout")
        
        signal.signal(signal.SIGALRM, agent_timeout_handler)
        signal.alarm(120)  # 2 minute timeout for OpenAI operations
        
        try:
            # Import and run the tournament summary agent
            from agents.tournament_summary import run_tournament_summary_agent as run_agent
            result = run_agent()
            signal.alarm(0)  # Cancel timeout
            
            if result and result.get('status') == 'success':
                summaries_added = result.get('summaries_added', 0)
                
                if summaries_added > 0:
                    import datetime
                    now = datetime.datetime.now()
                    time_str = now.strftime("%B %d at %I:%M%p").lower()
                    flash(f"✅ Tournament Summary Agent ran successfully on {time_str} — {summaries_added} summaries added", 'success')
                else:
                    flash(f"✅ Tournament Summary Agent completed — all tournaments already have summaries", 'info')
            else:
                error_msg = result.get('message', 'Unknown error') if result else 'Agent returned no result'
                flash(f"❌ Tournament Summary Agent failed: {error_msg}", 'danger')
        except TimeoutError:
            signal.alarm(0)
            flash("❌ Tournament Summary Agent timed out — operation took too long", 'danger')
        finally:
            signal.alarm(0)  # Ensure timeout is cancelled
            
    except Exception as e:
        logger.error(f"Error running tournament summary agent: {str(e)}", exc_info=True)
        flash(f"❌ Error running Tournament Summary Agent: Check logs for details", 'danger')
    
    return redirect(url_for('admin_agents.agents_dashboard'))

@admin_agents_bp.route('/run/lanyard_reminder', methods=['POST'])
def run_lanyard_reminder_route():
    """Execute the lanyard reminder agent manually"""
    try:
        logger.info(f"Admin {current_user.email} triggered lanyard reminder agent")
        
        # Set a timeout for the entire operation
        import signal
        
        def agent_timeout_handler(signum, frame):
            raise TimeoutError("Agent execution timeout")
        
        signal.signal(signal.SIGALRM, agent_timeout_handler)
        signal.alarm(60)  # 1 minute timeout for lanyard reminder operations
        
        try:
            # Import and run the lanyard reminder agent
            result = run_lanyard_agent()
            signal.alarm(0)  # Cancel timeout
            
            if result:
                import datetime
                now = datetime.datetime.now()
                time_str = now.strftime("%B %d at %I:%M%p").lower()
                flash(f"✅ Lanyard Reminder Agent ran successfully on {time_str} — {result}", 'success')
            else:
                flash(f"✅ Lanyard Reminder Agent completed — no qualifying users found", 'info')
                
        except TimeoutError:
            signal.alarm(0)
            flash("❌ Lanyard Reminder Agent timed out — operation took too long", 'danger')
        finally:
            signal.alarm(0)  # Ensure timeout is cancelled
            
    except Exception as e:
        logger.error(f"Error running lanyard reminder agent: {str(e)}", exc_info=True)
        flash(f"❌ Error running Lanyard Reminder Agent: Check logs for details", 'danger')
    
    return redirect(url_for('admin_agents.agents_dashboard'))

@admin_agents_bp.route('/run/post_event_followup', methods=['POST'])
def run_post_event_followup():
    """Execute the post-event follow-up agent manually"""
    try:
        logger.info(f"Admin {current_user.email} triggered post-event follow-up agent")
        
        # Set a timeout for the entire operation
        import signal
        
        def agent_timeout_handler(signum, frame):
            raise TimeoutError("Agent execution timeout")
        
        signal.signal(signal.SIGALRM, agent_timeout_handler)
        signal.alarm(60)  # 1 minute timeout for post-event follow-up operations
        
        try:
            # Import and run the post-event follow-up agent
            result = run_post_event_followup_agent()
            signal.alarm(0)  # Cancel timeout
            
            if result:
                import datetime
                now = datetime.datetime.now()
                time_str = now.strftime("%B %d at %I:%M%p").lower()
                flash(f"✅ Post-Event Follow-Up Agent ran successfully on {time_str} — {result}", 'success')
            else:
                flash(f"✅ Post-Event Follow-Up Agent completed — no qualifying tournaments found", 'info')
                
        except TimeoutError:
            signal.alarm(0)
            flash("❌ Post-Event Follow-Up Agent timed out — operation took too long", 'danger')
        finally:
            signal.alarm(0)  # Ensure timeout is cancelled
            
    except Exception as e:
        logger.error(f"Error running post-event follow-up agent: {str(e)}", exc_info=True)
        flash(f"❌ Error running Post-Event Follow-Up Agent: Check logs for details", 'danger')
    
    return redirect(url_for('admin_agents.agents_dashboard'))

@admin_agents_bp.route('/run/pre_tournament_reminder', methods=['POST'])
def run_pre_tournament_reminder():
    """Execute the pre-tournament reminder agent manually"""
    try:
        logger.info(f"Admin {current_user.email} triggered pre-tournament reminder agent")
        
        # Set a timeout for the entire operation
        import signal
        
        def agent_timeout_handler(signum, frame):
            raise TimeoutError("Agent execution timeout")
        
        signal.signal(signal.SIGALRM, agent_timeout_handler)
        signal.alarm(60)  # 1 minute timeout for pre-tournament reminder operations
        
        try:
            # Import and run the pre-tournament reminder agent
            result = run_pre_tournament_reminder_agent()
            signal.alarm(0)  # Cancel timeout
            
            if result:
                import datetime
                now = datetime.datetime.now()
                time_str = now.strftime("%B %d at %I:%M%p").lower()
                flash(f"✅ Pre-Tournament Reminder Agent ran successfully on {time_str} — {result}", 'success')
            else:
                flash(f"✅ Pre-Tournament Reminder Agent completed — no qualifying users found", 'info')
                
        except TimeoutError:
            signal.alarm(0)
            flash("❌ Pre-Tournament Reminder Agent timed out — operation took too long", 'danger')
        finally:
            signal.alarm(0)  # Ensure timeout is cancelled
            
    except Exception as e:
        logger.error(f"Error running pre-tournament reminder agent: {str(e)}", exc_info=True)
        flash(f"❌ Error running Pre-Tournament Reminder Agent: Check logs for details", 'danger')
    
    return redirect(url_for('admin_agents.agents_dashboard'))

@admin_agents_bp.route('/edit/<agent_name>', methods=['GET', 'POST'])
def edit_agent_email(agent_name):
    """Edit email templates for agents"""
    filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'email_templates.json')
    
    try:
        with open(filepath, 'r') as f:
            templates = json.load(f)
    except FileNotFoundError:
        flash('Email templates file not found', 'error')
        return redirect(url_for('admin_agents.agents_dashboard'))
    except json.JSONDecodeError:
        flash('Error reading email templates file', 'error')
        return redirect(url_for('admin_agents.agents_dashboard'))

    if agent_name not in templates:
        flash(f'Template "{agent_name}" not found', 'error')
        return redirect(url_for('admin_agents.agents_dashboard'))

    if request.method == 'POST':
        try:
            templates[agent_name]['subject'] = request.form['subject']
            templates[agent_name]['body'] = request.form['body']
            
            with open(filepath, 'w') as f:
                json.dump(templates, f, indent=2)
                
            flash(f'Email template for "{agent_name}" updated successfully', 'success')
            return redirect(url_for('admin_agents.edit_agent_email', agent_name=agent_name))
        except Exception as e:
            logger.error(f"Error saving email template: {str(e)}")
            flash('Error saving email template', 'error')

    return render_template('admin/edit_agent_email.html',
                           agent_name=agent_name,
                           subject=templates[agent_name].get('subject', ''),
                           body=templates[agent_name].get('body', ''))

@admin_agents_bp.route('/blog-agent')
def blog_agent():
    """Blog Generator Agent - suggest SEO blog topics for upcoming tournaments"""
    # Get tournaments starting within the next 30 days
    thirty_days_from_now = datetime.now().date() + timedelta(days=30)
    today = datetime.now().date()
    
    upcoming_tournaments = Tournament.query.filter(
        Tournament.start_date >= today,
        Tournament.start_date <= thirty_days_from_now
    ).order_by(Tournament.start_date).all()
    
    return render_template('admin/blog_agent.html', tournaments=upcoming_tournaments)

@admin_agents_bp.route('/blog-agent/suggest/<int:tournament_id>', methods=['POST'])
def suggest_blog_topics(tournament_id):
    """Generate blog topic suggestions for a specific tournament using OpenAI"""
    try:
        tournament = Tournament.query.get_or_404(tournament_id)
        
        # Initialize OpenAI client
        openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        
        # Create prompt for OpenAI
        prompt = f"Suggest 5 blog post titles for {tournament.name} that are helpful to first-time attendees or casual tennis fans. Include travel tips, what to expect, what to bring, or venue-specific ideas. Keep them SEO-friendly."
        
        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates SEO-friendly blog post titles for tennis tournaments. Respond with exactly 5 titles, one per line, without numbering or bullet points."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        # Extract and format the topics
        topics_text = response.choices[0].message.content.strip()
        topics = [topic.strip() for topic in topics_text.split('\n') if topic.strip()]
        
        # Ensure we have exactly 5 topics
        topics = topics[:5]
        
        # Assign topic types based on keywords
        topic_data = []
        for topic in topics:
            topic_type = "Guide"
            if any(word in topic.lower() for word in ["tip", "tips"]):
                topic_type = "Tips"
            elif any(word in topic.lower() for word in ["pack", "bring", "what to"]):
                topic_type = "Packing List"
            elif any(word in topic.lower() for word in ["travel", "getting", "how to get"]):
                topic_type = "Travel"
            elif any(word in topic.lower() for word in ["expect", "experience", "first time"]):
                topic_type = "Guide"
            
            topic_data.append({
                'title': topic,
                'type': topic_type
            })
        
        return jsonify({
            'success': True,
            'tournament_name': tournament.name,
            'topics': topic_data
        })
        
    except Exception as e:
        logger.error(f"Error generating blog topics for tournament {tournament_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to generate blog topics. Please try again.'
        }), 500

