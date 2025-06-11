from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from agents.email_reminder import run_email_reminder
import logging

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
        preview_mode = request.form.get('preview_mode') == 'on'
        logger.info(f"Admin {current_user.email} triggered email reminder agent (preview: {preview_mode})")
        
        # Run the email reminder agent
        result = run_email_reminder(preview_mode=preview_mode)
        
        if result['status'] == 'success':
            emails_sent = result.get('emails_sent', 0)
            tournaments_processed = result.get('tournaments_processed', 0)
            
            if preview_mode:
                flash(f"✅ Email Reminder Agent preview completed — would have sent {emails_sent} emails for {tournaments_processed} tournament(s)", 'info')
            else:
                if emails_sent > 0:
                    import datetime
                    now = datetime.datetime.now()
                    time_str = now.strftime("%B %d at %I:%M%p").lower()
                    flash(f"✅ Email Reminder Agent ran successfully on {time_str} — {emails_sent} users emailed", 'success')
                else:
                    flash(f"✅ Email Reminder Agent completed — no emails needed at this time", 'info')
        else:
            flash(f"❌ Email Reminder Agent failed: {result['message']}", 'danger')
            
    except Exception as e:
        logger.error(f"Error running email reminder agent: {str(e)}", exc_info=True)
        flash(f"❌ Error running Email Reminder Agent: {str(e)}", 'danger')
    
    return redirect(url_for('admin_agents.agents_dashboard'))

@admin_agents_bp.route('/run/tournament_summary', methods=['POST'])
def run_tournament_summary_agent():
    """Execute the tournament summary agent manually"""
    try:
        logger.info(f"Admin {current_user.email} triggered tournament summary agent")
        flash("Tournament Summary Agent: This feature is coming soon!", 'info')
    except Exception as e:
        logger.error(f"Error running tournament summary agent: {str(e)}", exc_info=True)
        flash(f"Error running Tournament Summary Agent: {str(e)}", 'error')
    
    return redirect(request.referrer or url_for('admin_agents.agents_dashboard'))

@admin_agents_bp.route('/run/blog_generator', methods=['POST'])
def run_blog_generator_agent():
    """Execute the blog generator agent manually"""
    try:
        logger.info(f"Admin {current_user.email} triggered blog generator agent")
        flash("Blog Generator Agent: This feature is coming soon!", 'info')
    except Exception as e:
        logger.error(f"Error running blog generator agent: {str(e)}", exc_info=True)
        flash(f"Error running Blog Generator Agent: {str(e)}", 'error')
    
    return redirect(request.referrer or url_for('admin_agents.agents_dashboard'))

@admin_agents_bp.route('/run/social_caption', methods=['POST'])
def run_social_caption_agent():
    """Execute the social caption agent manually"""
    try:
        logger.info(f"Admin {current_user.email} triggered social caption agent")
        flash("Social Caption Agent: This feature is coming soon!", 'info')
    except Exception as e:
        logger.error(f"Error running social caption agent: {str(e)}", exc_info=True)
        flash(f"Error running Social Caption Agent: {str(e)}", 'error')
    
    return redirect(request.referrer or url_for('admin_agents.agents_dashboard'))

@admin_agents_bp.route('/run/post_event_followup', methods=['POST'])
def run_post_event_followup_agent():
    """Execute the post-event follow-up agent manually"""
    try:
        logger.info(f"Admin {current_user.email} triggered post-event follow-up agent")
        flash("Post-Event Follow-Up Agent: This feature is coming soon!", 'info')
    except Exception as e:
        logger.error(f"Error running post-event follow-up agent: {str(e)}", exc_info=True)
        flash(f"Error running Post-Event Follow-Up Agent: {str(e)}", 'error')
    
    return redirect(request.referrer or url_for('admin_agents.agents_dashboard'))

@admin_agents_bp.route('/run/lanyard_reminder', methods=['POST'])
def run_lanyard_reminder_agent():
    """Execute the lanyard reminder agent manually"""
    try:
        logger.info(f"Admin {current_user.email} triggered lanyard reminder agent")
        flash("Lanyard Reminder Agent: This feature is coming soon!", 'info')
    except Exception as e:
        logger.error(f"Error running lanyard reminder agent: {str(e)}", exc_info=True)
        flash(f"Error running Lanyard Reminder Agent: {str(e)}", 'error')
    
    return redirect(request.referrer or url_for('admin_agents.agents_dashboard'))