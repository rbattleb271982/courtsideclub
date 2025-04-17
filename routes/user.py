from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from replit import db
from services.printful import create_lanyard_order
from services.sendgrid_service import send_email
import json

# Initialize blueprint
user_bp = Blueprint('user', __name__)

@user_bp.route('/profile')
@login_required
def profile():
    # Get all tournaments
    tournaments = db.get('tournaments', [])
    
    # Get user data
    user_data = db.get(current_user.id, {})
    
    # Get attending tournaments
    attending_ids = user_data.get('attending', [])
    attending = [t for t in tournaments if t['id'] in attending_ids]
    
    return render_template('profile.html', 
                          user=current_user,
                          attending=attending,
                          all_tournaments=tournaments)

@user_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name')
    notifications = 'notifications' in request.form
    
    # Update user in database
    user_data = db.get(current_user.id, {})
    if name:
        user_data['name'] = name
    user_data['notifications'] = notifications
    db[current_user.id] = user_data
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('user.profile'))

@user_bp.route('/profile/attending', methods=['POST'])
@login_required
def update_attending():
    # Get the tournaments the user wants to attend
    attending = request.form.getlist('attending')
    
    # Update user in database
    user_data = db.get(current_user.id, {})
    user_data['attending'] = attending
    db[current_user.id] = user_data
    
    flash('Tournament preferences updated!', 'success')
    return redirect(url_for('user.profile'))

@user_bp.route('/toggle_notifications')
@login_required
def toggle_notifications():
    # Toggle notifications setting
    user_data = db.get(current_user.id, {})
    user_data['notifications'] = not user_data.get('notifications', True)
    db[current_user.id] = user_data
    
    status = "enabled" if user_data['notifications'] else "disabled"
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
            user_data = db.get(current_user.id, {})
            user_data['lanyard_ordered'] = True
            db[current_user.id] = user_data
            
            # Send confirmation email to user
            if user_data.get('notifications', True):
                send_email(
                    to_email=current_user.email,
                    subject="Your Tennis Fans Lanyard Order",
                    html_content=render_template('email/notification.html', 
                                                name=current_user.name,
                                                message="Your lanyard order has been placed! You'll receive it soon.")
                )
            
            # Send admin notification
            admin_email = current_app.config.get('ADMIN_EMAIL')
            if admin_email:
                send_email(
                    to_email=admin_email,
                    subject="New Lanyard Order",
                    html_content=render_template('email/admin_summary.html',
                                                user_email=current_user.email,
                                                user_name=current_user.name,
                                                order_id=order_id)
                )
            
            flash('Your lanyard has been ordered!', 'success')
            return redirect(url_for('user.profile'))
        
        except Exception as e:
            flash(f'There was a problem ordering your lanyard: {str(e)}', 'danger')
            return render_template('order_lanyard.html')
    
    return render_template('order_lanyard.html')
