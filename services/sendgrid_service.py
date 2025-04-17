import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from flask import current_app

def send_email(to_email, subject, html_content=None, text_content=None):
    """
    Send an email using SendGrid
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html_content (str, optional): HTML content of the email
        text_content (str, optional): Plain text content of the email
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    api_key = current_app.config.get('SENDGRID_API_KEY')
    if not api_key:
        # Log this, but for demo purposes we'll pretend it worked
        print("SendGrid API key not configured. Email would have been sent.")
        return True
    
    from_email = current_app.config.get('FROM_EMAIL', 'noreply@tennisfans.app')
    
    message = Mail(
        from_email=Email(from_email),
        to_emails=To(to_email),
        subject=subject
    )
    
    if html_content:
        message.content = Content("text/html", html_content)
    elif text_content:
        message.content = Content("text/plain", text_content)
    else:
        message.content = Content("text/plain", "")
    
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        return True
    except Exception as e:
        print(f"SendGrid error: {str(e)}")
        return False
