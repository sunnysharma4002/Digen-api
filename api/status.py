import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from digen_image_api import check_job_status, _load_config

app = Flask(__name__)


@app.route("/", methods=["GET", "OPTIONS"])
def handle():
    if request.method == "OPTIONS":
        return cors(jsonify({"ok": True}))

    job_id = request.args.get("job_id", "").strip()
    session_id = request.args.get("session_id", "").strip()
    token = request.args.get("token", "").strip()

    if not job_id or not session_id:
        return cors(jsonify({"error": "job_id and session_id required"}), 400)

    try:
        _, base_url = _load_config()
        result = check_job_status(job_id, session_id, base_url, token or None)
    except Exception as e:
        return cors(jsonify({"error": type(e).__name__ + ": " + str(e)}), 500)

    return cors(jsonify(result))


def cors(response, status_code=200):
    response.status_code = status_code
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
