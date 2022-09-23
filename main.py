import hashlib
from flask import Flask, render_template, redirect, url_for
from flask import request
from flask_cors import CORS
import requests
import yaml
import os
import json
from bson.json_util import dumps, loads
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.environ['MONGODB_URI']
COLLECTION = os.getenv("COLLECTION")
DB_NAME = os.getenv("DATABASE_NAME")
CERAMIC_BE = os.getenv("CERAMIC_BE")
CERAMIC_BE_PORT = os.getenv("CERAMIC_BE_PORT")
cluster = MongoClient(MONGODB_URI)
levelling = cluster[COLLECTION][DB_NAME]

app = Flask(__name__)
CORS(app)

with open("config.yaml", "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
API_ENDPOINT = config['API_ENDPOINT']

def gen_hashCode(member_id, guild_id):
    st = '{}_{}'.format(member_id, guild_id)
    return hashlib.sha256(st.encode('utf-8')).hexdigest()
    

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

@app.route('/api/decrypt')
def get_fromhashCode():
    hashCode = request.args.get('hashCode')
    user = levelling.find_one({'hashCode': hashCode})
    return {'user_id': str(user['user_id']), 'guild_id': str(user['guild_id'])}
    
@app.route('/api/fetch')
def fetch():
    user_id = request.args.get('user_id')
    guild_id = request.args.get('guild_id')
    user = levelling.find_one({'user_id': int(user_id), 'guild_id': int(guild_id)})
    print(user)
    return json.loads(dumps(user))

@app.route('/api/auth/discord/redirect')
def process():
    code = request.args.get('code')
    print(code)
    accessToken = exchange_code(code)
    print(accessToken)
    member = get_member(accessToken)
    print(member)
    user = levelling.find_one({'user_id': int(member['id'])})
    print(user)
    guild_id = int(user['verifyGuild'])
    hashCode = gen_hashCode(int(member['id']), guild_id)
    levelling.update_one({'user_id': int(member['id']), 'guild_id': guild_id}, {'$set': {'hashCode': hashCode}})
    #print("to call ceramic ..... on guild : {}, with member : {}".format(guild_id, user['user_id']))
    #streamId = requests.post('http://{}:{}/ceramic/write_profile'.format(CERAMIC_BE, CERAMIC_BE_PORT), json=data)
    #levelling.update_one({'user_id': int(member['id'])}, {'$set': {'hashCode': streamId}})
    #You have already linked your Discord id with your wallet address.
    #7FdCH5ehUCgF7JNu4Qtb2seBevXt2fcyN9qqSNa2vXZd
    #return render_template('index.html')
    return redirect('https://connect.mushroom.social?hash={}'.format(hashCode))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3333, ssl_context=('fullchain.pem', 'privkey.pem'))
