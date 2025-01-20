# Python standard libraries
import json
import os
from datetime import datetime

# Third party libraries
from flask import Flask, redirect, request, url_for, Response
from oauthlib.oauth2 import WebApplicationClient
import requests

current_user = {}

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

# Flask app setup
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)


# OAuth2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)


def timestamp():
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    return '>>>> A bejelentkezés időpontja: ' + current_time + '\n'


@app.route("/")
def index():
    if current_user:
        return (
            "<p>Hello, {}! You're logged in! Email: {}</p>"
            "<div><p>Google Profile Picture:</p>"
            '<img src="{}" alt="Google profile pic"></img></div>'
            '<a class="button" href="/logout">Logout</a>'.format(
                current_user.name, current_user.email, current_user.profile_pic
            )
        )
    else:
        return '<a class="button" href="/login">Google Login</a>'


@app.route("/login")
def login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )
    # print('request_uri:')
    # print(request_uri)
    return redirect(request_uri)


@app.route("/login/callback")
def callback():
    # Get authorization code Google sent back to you
    code = request.args.get("code")
    log = open('login.txt', 'a', encoding='utf-8')
    print(f'code: {code}', file=log)

    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send request to get tokens! Yay tokens!
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )
    print(f'{token_url=}', file=log)
    print(f'{headers=}', file=log)
    print(f'{body=}', file=log)
    # print(f'{request.url=}\n{request.base_url=}\n{code=}\n{token_url=}\n{headers}\n{body=}')
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )

    # Parse the tokens!
    tp = client.parse_request_body_response(json.dumps(token_response.json()))
    print(f'{tp=}', file=log)
    # Now that we have tokens (yay) let's find and hit URL
    # from Google that gives you user's profile information,
    # including their Google Profile Image and Email
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    print(f'{uri=}' , file=log)
    print(f'{headers=}', file=log)
    print(f'{body=}', file=log)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    print(f'{userinfo_response=}', file=log)

    print(timestamp(), file=log)
    log.close()
    # We want to make sure their email is verified.
    # The user authenticated with Google, authorized our
    # app, and now we've verified their email through Google!
    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["given_name"]
        resp = {
            'email': users_email,
            'name': users_name
        }

    else:
        return "User email not available or not verified by Google.", 400

    # Send user back to homepage
    # return redirect(url_for("index"))
    return Response(response=json.dumps(resp),
                    headers={"Access-Control-Allow-Origin": "*"},
                    content_type="application/json")



def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()


if __name__ == "__main__":
    app.run(ssl_context="adhoc")
