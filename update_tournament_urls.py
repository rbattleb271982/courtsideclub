"""
Update tournament official URLs in the database
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Tournament URL mapping
tournament_urls = {
    "Abierto Mexicano Telcel (Acapulco)": "https://abiertomexicanodetenis.com/en/",
    "Australian Open": "https://ausopen.com/",
    "Barcelona Open Banc Sabadell": "https://www.atptour.com/en/tournaments/barcelona/425/overview",
    "Swiss Indoors Basel": "https://www.swissindoorsbasel.ch/en/",
    "China Open (Beijing)": "https://www.chinaopen.com/en/",
    "bett1open (Berlin)": "https://www.berlintennisopen.com/en",
    "National Bank Open (Canada)": "https://nationalbankopen.com/",
    "Credit One Charleston Open": "https://www.creditonecharlestonopen.com/",
    "Western & Southern Open (Cincinnati)": "https://www.wsopen.com/",
    "Qatar TotalEnergies Open (Doha)": "https://www.qatartennis.org/tournaments/qatar-totalenergies-open/",
    "Dubai Duty Free Tennis Championships (WTA)": "https://dubaidutyfreetennischampionships.com/",
    "Gonet Geneva Open": "https://gonetgenevaopen.com/",
    "Hobart International": "https://www.hobartinternational.com.au/",
    "BNP Paribas Open (Indian Wells)": "https://bnpparibasopen.com/",
    "Open 6ème Sens (Lyon)": "https://open6emesens.fr/",
    "Madrid Open": "https://www.madrid-open.com/en/",
    "Miami Open": "https://www.miamiopen.com/",
    "Monte Carlo Masters": "https://montecarlotennismasters.com/en/",
    "Rothesay Open Nottingham": "https://www.lta.org.uk/fan-zone/international/rothesay-open-nottingham/",
    "Rolex Paris Masters": "https://www.rolexparismasters.com/en",
    "Cinch Championships (Queen's Club)": "https://www.lta.org.uk/fan-zone/international/cinch-championships/",
    "Rio Open": "https://rioopen.com/",
    "Roland Garros (French Open)": "https://www.rolandgarros.com/en-us/",
    "Internazionali BNL d'Italia (Rome)": "https://www.internazionalibnlditalia.com/en/",
    "ABN AMRO Open (Rotterdam)": "https://www.abnamro-open.nl/en",
    "San Diego Open": "https://barnessdopen.com/",
    "Rolex Shanghai Masters": "https://en.rolexshanghaimasters.com/",
    "US Open": "https://www.usopen.org/",
    "Mubadala Citi DC Open": "https://www.mubadalacitidcopen.com/",
    "Wimbledon": "https://www.wimbledon.com/",
    "Winston-Salem Open": "https://www.winstonsalemopen.com/"
}

def update_tournament_urls():
    """Update the external_url field for tournaments based on name matching"""
    session = Session()
    
    try:
        updated_count = 0
        not_found = []
        
        for tournament_name, url in tournament_urls.items():
            # Update tournament by name
            result = session.execute(
                text("UPDATE tournaments SET external_url = :url WHERE name = :name"),
                {"url": url, "name": tournament_name}
            )
            
            if result.rowcount > 0:
                print(f"✓ Updated: {tournament_name}")
                updated_count += 1
            else:
                print(f"✗ Not found: {tournament_name}")
                not_found.append(tournament_name)
        
        # Commit all changes
        session.commit()
        
        print(f"\n=== UPDATE SUMMARY ===")
        print(f"Total tournaments processed: {len(tournament_urls)}")
        print(f"Successfully updated: {updated_count}")
        print(f"Not found: {len(not_found)}")
        
        if not_found:
            print(f"\nTournaments not found in database:")
            for name in not_found:
                print(f"  - {name}")
        
        # Verify a few updates
        print(f"\n=== VERIFICATION ===")
        verification_names = ["Roland Garros (French Open)", "US Open", "Wimbledon"]
        for name in verification_names:
            result = session.execute(
                text("SELECT name, external_url FROM tournaments WHERE name = :name"),
                {"name": name}
            ).fetchone()
            
            if result:
                print(f"✓ {result[0]}: {result[1]}")
            else:
                print(f"✗ {name}: Not found")
                
    except Exception as e:
        session.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    update_tournament_urls()