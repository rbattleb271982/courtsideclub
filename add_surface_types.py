
"""
Database Migration to populate surface types for tournaments

This script sets the court surface (Hard/Clay/Grass) for each tournament in the database.
"""
from app import app
from models import db, Tournament

def add_surface_types():
    # Map of tournament names to their surfaces  
    surface_map = {
        "Hobart International": "Hard",
        "Australian Open": "Hard", 
        "Qatar TotalEnergies Open (Doha)": "Hard",
        "ABN AMRO Open (Rotterdam)": "Hard",
        "Dubai Duty Free Tennis Championships (WTA)": "Hard",
        "San Diego Open": "Hard",
        "Rio Open": "Clay",
        "Open 6ème Sens (Lyon)": "Hard",
        "Abierto Mexicano Telcel (Acapulco)": "Hard",
        "BNP Paribas Open (Indian Wells)": "Hard",
        "Miami Open": "Hard",
        "Credit One Charleston Open": "Clay",
        "Monte Carlo Masters": "Clay",
        "Barcelona Open Banc Sabadell": "Clay",
        "Madrid Open": "Clay",
        "Internazionali BNL d'Italia (Rome)": "Clay",
        "Gonet Geneva Open": "Clay",
        "Roland Garros (French Open)": "Clay",
        "Rothesay Open Nottingham": "Grass",
        "bett1open (Berlin)": "Grass",
        "Cinch Championships (Queen's Club)": "Grass",
        "Wimbledon": "Grass",
        "Mubadala Citi DC Open": "Hard",
        "National Bank Open (Canada)": "Hard",
        "Western & Southern Open (Cincinnati)": "Hard",
        "Winston-Salem Open": "Hard",
        "US Open": "Hard",
        "China Open (Beijing)": "Hard",
        "Rolex Shanghai Masters": "Hard",
        "Swiss Indoors Basel": "Hard",
        "Rolex Paris Masters": "Hard"
    }

    with app.app_context():
        updated = 0
        for name, surface in surface_map.items():
            tournament = Tournament.query.filter_by(name=name).first()
            if tournament:
                tournament.surface = surface
                updated += 1
            else:
                print(f"Tournament not found: {name}")
        
        db.session.commit()
        print(f"✅ Surfaces updated for {updated} tournaments.")

if __name__ == "__main__":
    add_surface_types()
