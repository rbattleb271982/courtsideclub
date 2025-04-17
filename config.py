import os

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'dev_secret_key')
    
    # Google OAuth configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    
    # SendGrid configuration
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@tennisfans.app')
    
    # Printful configuration
    PRINTFUL_API_KEY = os.environ.get('PRINTFUL_API_KEY')
    
    # Admin email for notifications
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@tennisfans.app')
