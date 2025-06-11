from flask import Blueprint, render_template, request, redirect, url_for
from agents.email_reminder import run_email_reminder

admin_agents_bp = Blueprint('admin_agents', __name__)

@admin_agents_bp.route('/admin/agents')
def agents_dashboard():
    return render_template('admin/agents.html')

@admin_agents_bp.route('/admin/agents/run/<agent_name>', methods=['POST'])
def run_agent(agent_name):
    if agent_name == 'email_reminder':
        result = run_email_reminder()
        print(result)
    return redirect(url_for('admin_agents.agents_dashboard'))
