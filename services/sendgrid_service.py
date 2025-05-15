import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask import current_app

def send_email(to_email, subject, content_html):
    """
    Send an email using SendGrid
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        content_html (str): HTML content of the email
        
    Returns:
        int or None: Status code if email was sent successfully, None otherwise
    """
    from_email = current_app.config.get('FROM_EMAIL', 'noreply@courtsideclub.app')
    
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=content_html
    )
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(f"Email sent to {to_email}: {response.status_code}")
        return response.status_code
    except Exception as e:
        print(f"Error sending email: {e}")
        return None
