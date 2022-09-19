from flask import Flask, render_template
from flask import request
import requests
import yaml
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.environ['MONGODB_URI']
COLLECTION = os.getenv("COLLECTION")
DB_NAME = os.getenv("DATABASE_NAME")
cluster = MongoClient(MONGODB_URI)
levelling = cluster[COLLECTION][DB_NAME]

app = Flask(__name__)

with open("config.yaml", "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
API_ENDPOINT = config['API_ENDPOINT']

def exchange_code(code):
    CLIENT_ID = config['CLIENT_ID']
    CLIENT_SECRET = config['CLIENT_SECRET']
    REDIRECT_URI = config['REDIRECT_URI'] 
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    r = requests.post('%s/oauth2/token' % API_ENDPOINT, data=data, headers=headers)
    r.raise_for_status()
    return r.json()

def get_member(accessToken):
    headers = {
        'Authorization': '{} {}'.format(accessToken['token_type'], accessToken['access_token'])
    }
    r = requests.get('%s/users/@me' % API_ENDPOINT, headers=headers)
    r.raise_for_status()
    return r.json()

@app.route('/api/auth/discord/redirect')
def redirect():
    code = request.args.get('code')
    print(code)
    accessToken = exchange_code(code)
    print(accessToken)
    member = get_member(accessToken)
    print(member)
    user = levelling.find_one({'user_id': int(member['id'])})
    print(user)
    guild_id = int(user['verifyGuild'])
    print("to call ceramic ..... on guild : {}, with member : {}".format(guild_id, user['user_id']))
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3333, ssl_context=('fullchain.pem', 'privkey.pem'))