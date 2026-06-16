import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from digen_image_api import generate, submit_only, check_job_status, MODELS

app = Flask(__name__)


@app.route("/", methods=["GET"])
def handle_root():
    return cors(jsonify({
        "message": "Digen Image API",
        "endpoints": {
            "generate": "/generate?prompt=...&model=flux&mode=sync|async",
            "status": "/status?job_id=...&session_id=..."
        },
        "models": list(MODELS.keys()),
    }))


@app.route("/generate", methods=["GET", "POST", "OPTIONS"])
def handle_generate():
    if request.method == "OPTIONS":
        return cors(jsonify({"ok": True}))

    prompt = (request.args.get("prompt")
              or (request.json or {}).get("prompt")
              or "").strip()
    model = (request.args.get("model")
             or (request.json or {}).get("model")
             or "flux").strip()
    token = (request.args.get("token")
             or (request.json or {}).get("token")
             or "").strip()
    mode = (request.args.get("mode")
            or (request.json or {}).get("mode")
            or "sync").strip()

    if not prompt:
        return cors(jsonify({"error": "Prompt is required"}), 400)

    if mode == "async":
        result = submit_only(prompt, model, token or None)
    else:
        result = generate(prompt, model, token or None)

    code = 200 if result.get("success") else 502
    return cors(jsonify(result), code)


@app.route("/status", methods=["GET", "OPTIONS"])
def handle_status():
    if request.method == "OPTIONS":
        return cors(jsonify({"ok": True}))

    job_id = request.args.get("job_id", "").strip()
    session_id = request.args.get("session_id", "").strip()
    token = request.args.get("token", "").strip()

    if not job_id or not session_id:
        return cors(jsonify({"error": "job_id and session_id required"}), 400)

    from config import BASE_URL
    result = check_job_status(job_id, session_id, BASE_URL, token or None)
    return cors(jsonify(result))


def cors(response, status_code=200):
    response.status_code = status_code
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
