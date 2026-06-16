import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify
from digen_image_api import MODELS

app = Flask(__name__)


@app.route("/", methods=["GET"])
@app.route("/api", methods=["GET"])
def handle():
    return cors(jsonify({
        "message": "Digen Image API",
        "endpoints": {
            "generate": "/api/generate?prompt=...&model=flux&mode=sync|async",
            "status": "/api/status?job_id=...&session_id=..."
        },
        "models": list(MODELS.keys()),
    }))


def cors(response, status_code=200):
    response.status_code = status_code
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
