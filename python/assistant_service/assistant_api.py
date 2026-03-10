from flask import Flask
from flask_cors import CORS

from assistant_routes import register_assistant_routes

app = Flask(__name__)
CORS(app)

register_assistant_routes(app)


@app.route("/health")
def health():
    return {"status": "assistant-ok"}