from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from models import db, User, Tournament
from services.printful import create_lanyard_order
from services.sendgrid_service import send_email
import json

# Initialize blueprint
user_bp = Blueprint('user', __name__)

@user_bp.route('/profile')
@login_required
def profile():
    # Get all tournaments
    tournaments = Tournament.query.all()
    
    # Get user data
    user = User.query.get(current_user.id)
    
    # Get attending tournaments
    attending_ids = user.attending if user.attending else []
    attending = Tournament.query.filter(Tournament.id.in_(attending_ids)).all() if attending_ids else []
    
    return render_template('profile.html', 
                          user=user,
                          attending=attending,
                          all_tournaments=tournaments)

@user_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    notifications = 'notifications' in request.form
    
    # Update user in database
    user = User.query.get(current_user.id)
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    user.notifications = notifications
    db.session.commit()
    
    # Clear temporary password after profile update (if exists)
    if 'temp_password' in session:
        del session['temp_password']
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('user.profile'))

@user_bp.route('/profile/attending', methods=['POST'])
@login_required
def update_attending():
    # Get the tournaments the user wants to attend
    attending = request.form.getlist('attending')
    
    # Update user in database
    user = User.query.get(current_user.id)
    user.attending = attending
    db.session.commit()
    
    flash('Tournament preferences updated!', 'success')
    return redirect(url_for('user.profile'))

@user_bp.route('/toggle_notifications')
@login_required
def toggle_notifications():
    # Toggle notifications setting
    user = User.query.get(current_user.id)
    user.notifications = not user.notifications
    db.session.commit()
    
    status = "enabled" if user.notifications else "disabled"
    flash(f'Notifications {status}!', 'success')
    return redirect(url_for('user.profile'))

@user_bp.route('/order_lanyard', methods=['GET', 'POST'])
@login_required
def order_lanyard():
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        address1 = request.form.get('address1')
        address2 = request.form.get('address2', '')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip')
        country = request.form.get('country')
        
        # Form validation
        if not all([name, address1, city, zip_code, country]):
            flash('Please fill out all required fields.', 'danger')
            return render_template('order_lanyard.html')
        
        # Create order through Printful
        try:
            order_id = create_lanyard_order({
                'name': name,
                'address1': address1,
                'address2': address2,
                'city': city,
                'state': state,
                'zip': zip_code,
                'country': country,
                'email': current_user.email
            })
            
            # Update user in database
            user = User.query.get(current_user.id)
            user.lanyard_ordered = True
            db.session.commit()
            
            # Send confirmation email to user
            if user.notifications:
                send_email(
                    to_email=user.email,
                    subject="Your CourtSide Club Lanyard Order",
                    html_content=render_template('email/notification.html', 
                                                name=user.get_full_name(),
                                                message="Your lanyard order has been placed! You'll receive it soon.")
                )
            
            # Send admin notification
            admin_email = current_app.config.get('ADMIN_EMAIL')
            if admin_email:
                send_email(
                    to_email=admin_email,
                    subject="New Lanyard Order",
                    html_content=render_template('email/admin_summary.html',
                                                user_email=user.email,
                                                user_name=user.get_full_name(),
                                                order_id=order_id)
                )
            
            flash('Your lanyard has been ordered!', 'success')
            return redirect(url_for('user.profile'))
        
        except Exception as e:
            flash(f'There was a problem ordering your lanyard: {str(e)}', 'danger')
            return render_template('order_lanyard.html')
    
    return render_template('order_lanyard.html')
