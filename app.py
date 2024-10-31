from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)

@app.route('/')
def home():
    return 'ok'

if __name__ == '__main__':
    app.run()

# pip install flask SQLAlchemy pymysql google-cloud-pubsub aiohttp aiofiles
# pip install fastapi uvicorn[standard] SQLAlchemy pymysql google-cloud-pubsub aiohttp aiofiles