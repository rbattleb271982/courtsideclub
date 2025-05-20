# Fixed lanyard routes for admin_routes.py

@admin_bp.route('/lanyards')
@login_required
def lanyard_fulfillment():
    """Admin view for lanyard fulfillment tracking"""
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Get all users who ordered lanyards
    users_with_lanyards = User.query.filter_by(lanyard_ordered=True).all()
    
    # Summary stats
    total_ordered = len(users_with_lanyards)
    total_sent = sum(1 for user in users_with_lanyards if user.lanyard_sent)
    total_not_sent = total_ordered - total_sent
    
    # Find the next upcoming tournament
    today = datetime.utcnow().date()
    next_tournament = Tournament.query.filter(Tournament.start_date >= today).order_by(Tournament.start_date).first()
    
    # Users with unsent lanyards who are attending the next tournament
    unsent_next_tournament = []
    if next_tournament:
        for user in users_with_lanyards:
            if not user.lanyard_sent:
                # Check if user is attending next tournament
                registration = UserTournament.query.filter_by(
                    user_id=user.id,
                    tournament_id=next_tournament.id,
                    attending=True
                ).first()
                
                if registration:
                    unsent_next_tournament.append(user)
    
    # Prepare lanyard fulfillment data
    lanyard_data = []
    
    for user in users_with_lanyards:
        # Get shipping address if available
        has_address = bool(ShippingAddress.query.filter_by(user_id=user.id).first())
        
        # Get first tournament the user is attending
        first_tournament = None
        first_tournament_date = None
        sessions = None
        
        user_tourneys = UserTournament.query.filter_by(
            user_id=user.id,
            attending=True
        ).join(Tournament).order_by(Tournament.start_date).all()
        
        if user_tourneys:
            first_tournament = Tournament.query.get(user_tourneys[0].tournament_id)
            if first_tournament:
                first_tournament_date = first_tournament.start_date
                sessions = user_tourneys[0].session_label
        
        lanyard_data.append({
            'user': user,
            'has_address': has_address,
            'first_tournament': first_tournament,
            'first_tournament_date': first_tournament_date,
            'sessions': sessions
        })
    
    # Sort by lanyard_sent (unsent first), then by first tournament date
    lanyard_data.sort(key=lambda x: (
        x['user'].lanyard_sent,  # False comes before True
        x['first_tournament_date'] if x['first_tournament_date'] else datetime(9999, 12, 31).date()  # Sort by tournament date
    ))
    
    return render_template(
        "admin_lanyard_fulfillment.html",
        lanyard_data=lanyard_data,
        total_ordered=total_ordered,
        total_sent=total_sent,
        total_not_sent=total_not_sent,
        next_tournament=next_tournament,
        unsent_next_tournament=unsent_next_tournament
    )

@admin_bp.route('/lanyards/update-status/<int:user_id>', methods=['POST'])
@login_required
def update_lanyard_status(user_id):
    """Update lanyard fulfillment status"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    status = request.form.get('status') == 'true'
    
    # Update user's lanyard status
    user.lanyard_sent = status
    
    # If marking as sent, record the timestamp
    if status:
        user.lanyard_sent_date = datetime.utcnow()
    else:
        user.lanyard_sent_date = None
    
    # Save changes
    db.session.commit()
    
    # Log the event
    event = Event()
    event.user_id = current_user.id
    event.name = "lanyard_fulfillment_update"
    event.event_data = {
        "target_user_id": user_id,
        "lanyard_sent": status,
        "timestamp": datetime.utcnow().isoformat()
    }
    db.session.add(event)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'sent': status,
        'date': user.lanyard_sent_date.strftime('%b %d, %Y %H:%M UTC') if user.lanyard_sent_date else None
    })

@admin_bp.route('/export-lanyards')
@login_required
def export_lanyards():
    """Export lanyard orders to CSV"""
    if not current_user.is_admin:
        flash("Access denied.", "danger")
        return redirect(url_for("main.public_home"))
    
    # Get all users who ordered lanyards
    users_with_lanyards = User.query.filter_by(lanyard_ordered=True).all()
    
    if not users_with_lanyards:
        flash("No lanyard orders found.", "info")
        return redirect(url_for("admin.lanyard_fulfillment"))
    
    # Prepare CSV data
    csv_data = []
    headers = ["Name", "Email", "Address", "First Tournament", "Sessions", "Lanyard Sent", "Sent Date"]
    
    for user in users_with_lanyards:
        # Get shipping address if available
        shipping_address = ""
        address = ShippingAddress.query.filter_by(user_id=user.id).first()
        if address:
            shipping_address = f"{address.name}, {address.address1}, {address.address2 or ''}, {address.city}, {address.state or ''}, {address.zip_code}, {address.country}"
        
        # Get first tournament the user is attending
        first_tournament_str = "None"
        sessions_str = "None"
        
        user_tourneys = UserTournament.query.filter_by(
            user_id=user.id,
            attending=True
        ).join(Tournament).order_by(Tournament.start_date).all()
        
        if user_tourneys:
            first_tourney = user_tourneys[0]
            tournament = Tournament.query.get(first_tourney.tournament_id)
            if tournament:
                first_tournament_str = f"{tournament.name} ({tournament.start_date.strftime('%b %d, %Y')})"
                sessions_str = first_tourney.session_label or "No sessions selected"
        
        row = [
            user.get_full_name(),
            user.email,
            shipping_address or "Not provided",
            first_tournament_str,
            sessions_str,
            "Yes" if user.lanyard_sent else "No",
            user.lanyard_sent_date.strftime('%b %d, %Y %H:%M UTC') if user.lanyard_sent_date else "Not sent"
        ]
        
        csv_data.append(row)
    
    # Generate CSV response
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(csv_data)
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=lanyard_fulfillment.csv"
    response.headers["Content-type"] = "text/csv"
    
    # Log the export event
    event = Event()
    event.user_id = current_user.id
    event.name = "lanyard_export"
    event.event_data = {"exported_count": len(users_with_lanyards)}
    db.session.add(event)
    db.session.commit()
    
    return response