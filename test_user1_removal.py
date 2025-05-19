from app import app, db
from models import User, UserTournament, UserPastTournament

with app.app_context():
    # Get User 1
    user1 = User.query.filter_by(email='testuser1@example.com').first()
    print(f"User 1: {user1.name} (ID: {user1.id})")
    
    # 1. First, let's save the current state for restoration later
    ut_roland = UserTournament.query.filter_by(user_id=user1.id, tournament_id='roland_garros').first()
    
    # 2. Now let's simulate un-enrolling from Roland Garros
    if ut_roland:
        print("\nStep 1: Removing Roland Garros attendance...")
        # Option 1: Mark as not attending
        # ut_roland.attending = False
        # db.session.commit()
        
        # Option 2: Delete the enrollment completely (this is what the app actually does)
        db.session.delete(ut_roland)
        db.session.commit()
        
        print("  ✓ Removed attendance for Roland Garros")
    
    # 3. Check stats after removing attendance
    attending_count = UserTournament.query.filter(
        UserTournament.tournament_id == 'roland_garros',
        UserTournament.attending == True
    ).count()
    
    meeting_count = UserTournament.query.filter(
        UserTournament.tournament_id == 'roland_garros',
        UserTournament.attending == True,
        UserTournament.wants_to_meet == True
    ).count()
    
    print(f"\nRoland Garros stats after removal:")
    print(f"- Attending users: {attending_count}")
    print(f"- Open to meeting: {meeting_count}")
    
    # 4. Get current past tournament IDs for restoration later
    past_tournaments = UserPastTournament.query.filter_by(user_id=user1.id).all()
    past_tournament_ids = [(pt.id, pt.tournament_id) for pt in past_tournaments]
    
    # 5. Delete all past tournaments
    print("\nStep 2: Removing all past tournaments...")
    for pt in past_tournaments:
        db.session.delete(pt)
    db.session.commit()
    
    # 6. Check shared past tournaments now
    print("\nShared past tournaments after removal:")
    
    # Get all users attending Roland Garros
    attending_users = UserTournament.query.filter(
        UserTournament.tournament_id == 'roland_garros',
        UserTournament.attending == True
    ).all()
    
    attending_user_ids = [ut.user_id for ut in attending_users]
    
    if attending_user_ids:
        # Get past tournaments of attending users
        past_tournament_counts = db.session.query(
            UserPastTournament.tournament_id, db.func.count(UserPastTournament.user_id).label('count')
        ).filter(
            UserPastTournament.user_id.in_(attending_user_ids)
        ).group_by(
            UserPastTournament.tournament_id
        ).all()
        
        if past_tournament_counts:
            for tournament_id, count in past_tournament_counts:
                print(f"- {tournament_id}: {count}")
        else:
            print("  ✓ No past tournaments visible (as expected)")
    else:
        print("  ✓ No attending users, so no past tournaments visible (as expected)")
        
    # Now let's restore everything for further testing
    print("\nRestoring original state for additional testing...")
    
    # 1. Restore Roland Garros attendance
    new_ut = UserTournament(
        user_id=user1.id,
        tournament_id='roland_garros',
        attending=True,
        wants_to_meet=True,
        session_label='Day 1 - Day, Day 2 - Day',
        attendance_type='attending'
    )
    db.session.add(new_ut)
    
    # 2. Restore past tournaments
    for _, tournament_id in past_tournament_ids:
        new_pt = UserPastTournament(
            user_id=user1.id,
            tournament_id=tournament_id
        )
        db.session.add(new_pt)
    
    db.session.commit()
    print("  ✓ Original state restored")
