"""
Fix homepage URL references in the admin_routes.py file.

This script updates all references to 'main.homepage' to 'main.public_home'
since we've moved the About page content to the homepage.
"""

import os
import re

def fix_homepage_references():
    """Find and replace all references to main.homepage with main.public_home"""
    
    # Files to check and update
    target_files = [
        'routes/admin_routes.py',
        'templates/admin_tournament_list.html',
        # Add more files if needed
    ]
    
    pattern = r'url_for\(["\']main\.homepage["\']\)'
    replacement = r'url_for("main.public_home")'
    
    for file_path in target_files:
        if not os.path.exists(file_path):
            print(f"File {file_path} not found, skipping...")
            continue
            
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Replace the pattern
        updated_content = re.sub(pattern, replacement, content)
        
        # Only write if changes were made
        if updated_content != content:
            with open(file_path, 'w') as file:
                file.write(updated_content)
            print(f"Updated {file_path}")
        else:
            print(f"No changes needed in {file_path}")

if __name__ == "__main__":
    fix_homepage_references()
    print("Homepage reference fixing completed!")