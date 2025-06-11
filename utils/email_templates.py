"""
Email Template Utility

Provides functions to load and process email templates from the configuration file.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

def load_email_template(template_name):
    """
    Load an email template from the configuration file.
    
    Args:
        template_name (str): The name of the template to load
        
    Returns:
        dict: Dictionary containing 'subject' and 'body' keys
    """
    try:
        filepath = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'email_templates.json')
        
        with open(filepath, 'r') as f:
            templates = json.load(f)
            
        if template_name not in templates:
            logger.warning(f"Template '{template_name}' not found, using default")
            return {
                'subject': f'CourtSide Club Notification',
                'body': 'Hey {{ user.first_name }},<br><br>This is a notification from CourtSide Club.<br><br>—<br>The Lounge is Courtside.'
            }
            
        return templates[template_name]
        
    except Exception as e:
        logger.error(f"Error loading email template '{template_name}': {str(e)}")
        return {
            'subject': f'CourtSide Club Notification',
            'body': 'Hey {{ user.first_name }},<br><br>This is a notification from CourtSide Club.<br><br>—<br>The Lounge is Courtside.'
        }

def render_template(template_text, **kwargs):
    """
    Simple template rendering function to replace {{ variable }} placeholders.
    
    Args:
        template_text (str): Template text with {{ variable }} placeholders
        **kwargs: Variables to substitute
        
    Returns:
        str: Rendered template text
    """
    result = template_text
    
    for key, value in kwargs.items():
        placeholder = f"{{{{ {key} }}}}"
        result = result.replace(placeholder, str(value))
        
    return result