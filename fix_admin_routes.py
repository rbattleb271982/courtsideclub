"""
Fix duplicate route declarations in admin_routes.py

This script removes the duplicate lanyard route implementations
and fixes StringIO import issues.
"""

import os
import sys
import re

def fix_duplicate_routes():
    """Fix the duplicate route declarations in admin_routes.py"""
    file_path = 'routes/admin_routes.py'
    
    # Read the file
    with open(file_path, 'r') as file:
        content = file.read()
    
    # First make sure io is imported
    if 'import io' not in content:
        content = content.replace(
            'import csv\nfrom datetime',
            'import csv\nimport io\nfrom datetime'
        )
    
    # Get route declarations and endpoints
    route_regex = r"@admin_bp\.route\('([^']+)'[^\n]*\n[^\n]*\ndef ([^\(]+)\("
    routes = re.findall(route_regex, content)
    
    # Find duplicates
    route_paths = {}
    function_names = {}
    
    for path, func_name in routes:
        if path in route_paths:
            route_paths[path].append(func_name)
        else:
            route_paths[path] = [func_name]
            
        if func_name in function_names:
            function_names[func_name].append(path)
        else:
            function_names[func_name] = [path]
    
    # Find duplicates
    duplicate_routes = [path for path, funcs in route_paths.items() if len(funcs) > 1]
    duplicate_funcs = [func for func, paths in function_names.items() if len(paths) > 1]
    
    if duplicate_routes or duplicate_funcs:
        print(f"Found duplicate routes: {duplicate_routes}")
        print(f"Found duplicate functions: {duplicate_funcs}")
        
        # Remove second lanyard_fulfillment implementation
        second_lanyard_pattern = re.compile(
            r"@admin_bp\.route\('/lanyards'\)\n@login_required\ndef lanyard_fulfillment\(\):[^@]*?(?=@admin_bp\.route)",
            re.DOTALL
        )
        
        matches = list(second_lanyard_pattern.finditer(content))
        if len(matches) > 1:
            # Keep the first implementation, remove others
            content = content[:matches[1].start()] + "\n\n" + content[matches[1].end():]
    
        # Remove second update_lanyard_status implementation if it exists
        second_update_pattern = re.compile(
            r"@admin_bp\.route\('/lanyards/update-status/[^']*'\)[^@]*?(?=@admin_bp\.route)",
            re.DOTALL
        )
        
        matches = list(second_update_pattern.finditer(content))
        if len(matches) > 1:
            # Keep the first implementation, remove others
            content = content[:matches[1].start()] + "\n\n" + content[matches[1].end():]
    
        # Write back to file
        with open(file_path, 'w') as file:
            file.write(content)
        
        print("Fixed duplicate routes in admin_routes.py")
    else:
        print("No duplicate routes found in admin_routes.py")

if __name__ == "__main__":
    fix_duplicate_routes()