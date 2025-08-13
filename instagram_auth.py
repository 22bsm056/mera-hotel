from flask import Flask, request, redirect
import os
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)

# Instagram OAuth Configuration
INSTAGRAM_APP_ID = os.getenv('INSTAGRAM_APP_ID')
INSTAGRAM_APP_SECRET = os.getenv('INSTAGRAM_APP_SECRET')
REDIRECT_URI = os.getenv('INSTAGRAM_REDIRECT_URI')

@app.route('/')
def handle_auth():
    code = request.args.get('code')
    if code:
        # Exchange code for access token
        token_url = f"https://api.instagram.com/oauth/access_token"
        data = {
            'client_id': INSTAGRAM_APP_ID,
            'client_secret': INSTAGRAM_APP_SECRET,
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'code': code
        }
        response = requests.post(token_url, data=data)
        return response.json()
    else:
        return "No authorization code received", 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000)