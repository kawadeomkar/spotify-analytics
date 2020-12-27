FROM python:3.9.1

WORKDIR usr/src/quart_sp
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# temp key
ENV WSGI_SECRET_KEY "super_secret_key"
