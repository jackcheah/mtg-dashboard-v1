"""
Quick debug script to check and fix tournament state
Run this while tournament_dashboard.py is running in another terminal
"""

import requests

# Check current state
response = requests.get('http://127.0.0.1:5001/get_state_info')
data = response.json()

print("=" * 50)
print("CURRENT STATE:")
print("=" * 50)
print(f"State: {data.get('current_state', 'UNKNOWN')}")
print(f"Message: {data.get('message', 'N/A')}")
print(f"Allowed actions: {data.get('allowed_actions', [])}")
print("=" * 50)

# If stuck in participants_loaded, try setup again
if data.get('current_state') == 'participants_loaded':
    print("\nAttempting to setup tournament...")
    setup_response = requests.post('http://127.0.0.1:5001/setup_tournament',
                                  json={},
                                  headers={'Content-Type': 'application/json'})
    setup_data = setup_response.json()
    print(f"Setup result: {setup_data.get('success')}")
    print(f"Message: {setup_data.get('message')}")
    if not setup_data.get('success'):
        print(f"Error: {setup_data.get('error')}")
        print(f"Details: {setup_data.get('error_details', 'N/A')}")
