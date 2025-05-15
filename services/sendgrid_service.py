import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content
from flask import current_app
from bs4 import BeautifulSoup

def send_email(to_email, subject, content_html, content_text=None):
    """
    Send an email using SendGrid with both HTML and plain text versions

    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        content_html (str): HTML content of the email
        content_text (str, optional): Plain text version of the email. If not provided,
                                     it will be generated from the HTML content.

    Returns:
        int or None: Status code if email was sent successfully, None otherwise
    """
    # Use a verified Gmail address for SendGrid
    from_email = 'richardbattlebaxter@gmail.com'  # Using your verified Gmail

    # Generate plain text content from HTML if not provided
    if not content_text:
        try:
            # Auto-generate fallback plain text
            content_text = BeautifulSoup(content_html, "html.parser").get_text(separator='\n')
        except Exception as e:
            print(f"Error generating plain text from HTML: {e}")
            # Fallback to a simple text version if parsing fails
            content_text = "Please view this email in an HTML-capable email client."

    # Create the email message
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject
    )
    
    # Add HTML content
    message.add_content(Content("text/html", content_html))
    
    # Add plain text content
    message.add_content(Content("text/plain", content_text))

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