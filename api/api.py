import time
from flask import Flask
from flask import request


app = Flask(__name__)

@app.route('/api/scan')
def get_current_time():
    domain = request.args.get('domain')
    return {
        "sitemap": ["angarasecurity.ru/soc", "angarasecurity.ru/mtdr", "angarasecurity.ru/echo"]
    }