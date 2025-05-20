import os

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'dev_secret_key')
    
    # Database configuration
    # Use a fallback SQLite database if the main database is unavailable
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Improved connection pool settings for better resilience
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # Verify connections before use
        "pool_recycle": 300,    # Recycle connections every 5 minutes
        "pool_timeout": 30,     # Wait longer for connection
        "max_overflow": 15      # Allow more overflow connections
    }
    
    # Google OAuth configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    
    # SendGrid configuration
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@courtsideclub.app')
    
    # Printful configuration
    PRINTFUL_API_KEY = os.environ.get('PRINTFUL_API_KEY')
    
    # Admin email for notifications
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@courtsideclub.app')
