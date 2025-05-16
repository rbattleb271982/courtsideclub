from flask import Blueprint, jsonify
from models import db, User, Tournament, UserTournament

attendance_debug_bp = Blueprint('attendance_debug', __name__)

@attendance_debug_bp.route('/debug/attendance-types')
def attendance_types():
    """View the attendance_type values in user_tournament records"""
    user_tournaments = UserTournament.query.all()
    result = []
    
    for ut in user_tournaments:
        # Get user and tournament info
        user = User.query.get(ut.user_id)
        tournament = Tournament.query.get(ut.tournament_id)
        
        if user and tournament:
            result.append({
                'id': ut.id,
                'user': user.email,
                'tournament': tournament.name,
                'attending': ut.attending,
                'attendance_type': ut.attendance_type,
                'session_label': ut.session_label,
                'created_at': ut.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return jsonify(result)