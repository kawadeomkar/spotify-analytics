from quart import Quart

import os

# import views
import quart_sp.auth
import quart_sp.main

app = Quart(__name__)
app.secret_key = os.environ['WSGI_SECRET_KEY']
