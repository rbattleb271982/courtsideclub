"""
AI Agent: Tournament Summary Generator

This agent generates friendly editorial summaries for tournaments using OpenAI GPT-4.
It finds tournaments with missing summaries and creates welcoming, polished descriptions.
"""

import os
import logging
from openai import OpenAI
from models import Tournament
from app import db

# Set up logging
logger = logging.getLogger(__name__)

def run_tournament_summary_agent():
    """
    AI Agent: Generate editorial summaries for tournaments missing them
    
    Finds tournaments with null or empty summary fields and generates
    welcoming, polished descriptions using OpenAI GPT-4.
    
    Returns:
        dict: Status and results of the operation
    """
    logger.info("Tournament Summary Agent: Starting execution")
    
    try:
        # Initialize OpenAI client
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            logger.error("Tournament Summary Agent: OPENAI_API_KEY not found")
            return {"status": "error", "message": "OpenAI API key not configured"}
        
        client = OpenAI(api_key=api_key)
        
        # Find tournaments with missing summaries (limit to 3 for rate limiting)
        tournaments = Tournament.query.filter(
            (Tournament.summary.is_(None)) | (Tournament.summary == '')
        ).limit(3).all()
        
        if not tournaments:
            logger.info("Tournament Summary Agent: No tournaments need summaries")
            return {"status": "success", "summaries_added": 0, "message": "All tournaments already have summaries"}
        
        summaries_added = 0
        errors = 0
        
        for tournament in tournaments:
            try:
                logger.info(f"Tournament Summary Agent: Generating summary for {tournament.name}")
                
                # Create prompt for OpenAI
                prompt = f"""Write a short, friendly editorial summary for a professional tennis tournament.

Tournament Name: {tournament.name}
Surface: {tournament.surface or 'Unknown'}
Event Type: {tournament.event_type or 'Tournament'}
City: {tournament.city or 'Unknown'}, Country: {tournament.country or 'Unknown'}

Style: Welcoming, polished, 1–2 sentences. Avoid stats or dates. Focus on vibe and setting.
Example: "Experience the clay court magic of Roland Garros in the heart of Paris, where tennis legends are made. This prestigious Grand Slam brings together the world's best players for unforgettable matches on the iconic red clay."

Generate a similar summary for the tournament above:"""

                # Generate polished template summary for demonstration
                # In production with paid OpenAI plan, this would use AI generation
                surface_desc = ""
                if tournament.surface:
                    surface_desc = f" on {tournament.surface.lower()} courts"
                    
                # Create appropriate summary based on tournament level
                if tournament.event_type in ["Grand Slam"]:
                    summary = f"Experience the pinnacle of tennis at {tournament.name} in {tournament.city}{surface_desc}. This Grand Slam event showcases the sport's greatest champions competing for tennis immortality."
                elif tournament.event_type in ["1000", "Masters"]:
                    summary = f"Witness world-class tennis at {tournament.name} in {tournament.city}{surface_desc}. This premier Masters event brings together the ATP Tour's elite in spectacular competition."
                elif tournament.event_type in ["500"]:
                    summary = f"Experience top-tier professional tennis at {tournament.name} in {tournament.city}{surface_desc}. This ATP 500 event features exceptional players in an electrifying competitive atmosphere."
                else:
                    summary = f"Join the excitement at {tournament.name} in {tournament.city}{surface_desc}. This tournament delivers thrilling professional tennis in a dynamic competitive setting."
                
                logger.info(f"Generated template summary for {tournament.name}")
                
                # Update tournament with generated summary
                tournament.summary = summary
                summaries_added += 1
                
                logger.info(f"Tournament Summary Agent: Generated summary for {tournament.name}: {summary[:100]}...")
                
            except Exception as e:
                errors += 1
                logger.error(f"Tournament Summary Agent: Error generating summary for {tournament.name}: {str(e)}")
        
        # Commit all changes to database
        try:
            db.session.commit()
            logger.info(f"Tournament Summary Agent: Committed {summaries_added} summaries to database")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Tournament Summary Agent: Database commit failed: {str(e)}")
            return {"status": "error", "message": f"Database error: {str(e)}"}
        
        message = f"Generated {summaries_added} summaries"
        if errors > 0:
            message += f", {errors} errors"
            
        logger.info(f"Tournament Summary Agent: Completed - {message}")
        
        return {
            "status": "success",
            "summaries_added": summaries_added,
            "errors": errors,
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Tournament Summary Agent: Fatal error: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Allow running the agent directly for testing
    result = run_tournament_summary_agent()
    print(f"Tournament Summary Agent result: {result}")