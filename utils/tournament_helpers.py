"""
Tournament helper functions for generating consistent tournament data structures.
"""

from datetime import timedelta


def generate_tournament_days(start_date, end_date):
    """
    Generate tournament days from start_date to end_date (inclusive).
    
    Args:
        start_date: datetime.date object for tournament start
        end_date: datetime.date object for tournament end
    
    Returns:
        List of dictionaries with day_num, date, and formatted fields
    """
    tournament_days = []
    
    if start_date and end_date:
        current_date = start_date
        day_num = 1
        
        while current_date <= end_date:
            tournament_days.append({
                'day_num': day_num,
                'date': current_date,
                'formatted': current_date.strftime('%A, %B %d')
            })
            current_date += timedelta(days=1)
            day_num += 1
    
    return tournament_days