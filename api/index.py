import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from digen_image_api import generate, submit_only, check_job_status, MODELS

app = Flask(__name__)


@app.route("/api/generate", methods=["GET", "POST", "OPTIONS"])
def handle_generate():
    if request.method == "OPTIONS":
        return cors(jsonify({"ok": True}))

    prompt = _get_param("prompt")
    model = _get_param("model", "flux")
    token = _get_param("token", "")
    mode = _get_param("mode", "sync")  # 'sync' or 'async'

    if not prompt:
        return cors(jsonify({"error": "Prompt is required"}), 400)

    if mode == "async":
        result = submit_only(prompt, model, token or None)
    else:
        result = generate(prompt, model, token or None)

    code = 200 if result.get("success") else 502
    return cors(jsonify(result), code)


@app.route("/api/status", methods=["GET", "OPTIONS"])
def handle_status():
    if request.method == "OPTIONS":
        return cors(jsonify({"ok": True}))

    job_id = _get_param("job_id")
    session_id = _get_param("session_id")
    token = _get_param("token", "")

    if not job_id or not session_id:
        return cors(jsonify({"error": "job_id and session_id required"}), 400)

    from config import BASE_URL
    result = check_job_status(job_id, session_id, BASE_URL, token or None)
    return cors(jsonify(result))


@app.route("/api", methods=["GET"])
def handle_root():
    return cors(jsonify({
        "message": "Digen Image API",
        "usage": "GET /api/generate?prompt=...&model=flux&mode=sync|async",
        "models": list(MODELS.keys()),
    }))


def _get_param(name, default=""):
    return (request.args.get(name)
            or (request.json or {}).get(name)
            or default).strip()


def cors(response, status_code=200):
    response.status_code = status_code
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


handler = app
