from flask import Flask

import spotipy

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'hello world!'
