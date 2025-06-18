from datetime import timedelta

def generate_tournament_days(start_date, end_date):
    if not start_date or not end_date:
        return []

    tournament_days = []
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