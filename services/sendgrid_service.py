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
    # Get the FROM_EMAIL from config, or use default
    from_email = current_app.config.get('FROM_EMAIL', 'your_verified_email@example.com')
    
    # Create the email message
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=content_html  # SendGrid expects 'html_content', but our function uses 'content_html'
    )
    
    try:
        # Get API key from environment
        api_key = os.environ.get('SENDGRID_API_KEY')
        
        # Debug logging
        if not api_key:
            print("WARNING: SENDGRID_API_KEY environment variable is not set or empty")
        else:
            print(f"Using SendGrid API key: {api_key[:5]}...{api_key[-4:] if len(api_key) > 9 else ''}")
        
        # Initialize SendGrid client with API key
        sg = SendGridAPIClient(api_key)
        
        # Send the email
        response = sg.send(message)
        print(f"Email sent to {to_email}: {response.status_code}")
        return response.status_code
    except Exception as e:
        print(f"Error sending email: {e}")
        return None
