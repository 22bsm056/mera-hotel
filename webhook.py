from flask import Flask, request
import json
import os  # For managing the privacy policy file path

app = Flask(__name__)

# Path to the privacy policy HTML file (ensure it exists in the same directory)
PRIVACY_POLICY_FILE = 'privacy_policy.html'

# --- Privacy Policy Endpoint ---
@app.route('/privacy-policy')
def privacy_policy():
    """
    Serves the privacy policy HTML file required by Meta for app verification.
    """
    try:
        with open(PRIVACY_POLICY_FILE, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "Privacy Policy HTML file not found.", 404
    except Exception as e:
        return f"An error occurred while loading the privacy policy: {e}", 500

# --- Webhook Endpoint ---
@app.route('/')
def hello_world():
    return "<p>Hello, World! This is the Hotel Agent Webhook Service.</p>"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        try:
            print(json.dumps(request.get_json(), indent=4))
        except:
            pass
        return "<p>Webhook received! post request</p>"
    
    if request.method == 'GET':
        hub_mode = request.args.get('hub.mode')
        hub_challenge = request.args.get('hub.challenge')  # Fixed variable name (was hub.challenge)
        hub_verify_token = request.args.get('hub.verify_token')
        
        if hub_challenge:
            return hub_challenge
        return "<p>Webhook received! get request</p>"

# --- Flask Application Runner ---
if __name__ == '__main__':
    print(" Starting Flask application on http://127.0.0.1:5000")
    print(" Privacy Policy endpoint: http://127.0.0.1:5000/privacy-policy")
    print(" Webhook endpoint: http://127.0.0.1:5000/webhook")
    app.run(port=5000)