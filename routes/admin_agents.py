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

@admin_agents_bp.route('/run/email_reminder', methods=['POST'])
def run_email_reminder_agent():
    """Execute the email reminder agent manually"""
    try:
        logger.info(f"Admin {current_user.email} triggered email reminder agent")
        
        # Run the email reminder agent
        result = run_email_reminder()
        
        if result['status'] == 'success':
            flash(f"Email Reminder Agent completed successfully: {result['message']}", 'success')
        else:
            flash(f"Email Reminder Agent failed: {result['message']}", 'error')
            
    except Exception as e:
        logger.error(f"Error running email reminder agent: {str(e)}", exc_info=True)
        flash(f"Error running Email Reminder Agent: {str(e)}", 'error')
    
    return redirect(url_for('admin_agents.agents_dashboard'))