import os
import requests
import json
from flask import current_app

def create_lanyard_order(shipping_info):
    """
    Create a lanyard order through Printful API
    
    Args:
        shipping_info (dict): Customer shipping information
    
    Returns:
        str: Order ID if successful
        
    Raises:
        Exception: If the API call fails
    """
    api_key = current_app.config.get('PRINTFUL_API_KEY')
    if not api_key:
        raise Exception("Printful API key is not configured")
    
    # Printful API endpoint for creating orders
    url = "https://api.printful.com/orders"
    
    # Prepare the order data
    order_data = {
        "recipient": {
            "name": shipping_info['name'],
            "address1": shipping_info['address1'],
            "address2": shipping_info.get('address2', ''),
            "city": shipping_info['city'],
            "state_code": shipping_info.get('state', ''),
            "country_code": shipping_info['country'],
            "zip": shipping_info['zip'],
            "email": shipping_info['email']
        },
        "items": [
            {
                "variant_id": 1234,  # Replace with actual Printful lanyard variant ID
                "quantity": 1,
                "name": "Tennis Fans Lanyard",
                "retail_price": "12.99",
                "files": [
                    {
                        "url": "https://cdn.example.com/lanyard_design.png"  # Replace with actual design URL
                    }
                ]
            }
        ]
    }
    
    # Make the API request
    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            data=json.dumps(order_data)
        )
        
        # Check for successful response
        if response.status_code == 200:
            result = response.json()
            return result['result']['id']
        else:
            # For demo purposes, let's simulate a successful order when API key isn't available
            if not api_key:
                return "SIMULATED_ORDER_12345"
            
            # Otherwise, raise an error with the API response
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            raise Exception(f"Printful API error: {error_msg}")
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"Request error: {str(e)}")
