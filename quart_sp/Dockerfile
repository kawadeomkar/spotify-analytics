FROM python:3.8.6

WORKDIR usr/src/flask_app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# temp key
ENV WSGI_SECRET_KEY "super_secret_key"
