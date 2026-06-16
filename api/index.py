import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from digen_image_api import generate, submit_only, check_job_status, _load_config, MODELS

app = Flask(__name__)


@app.route("/", methods=["GET"])
@app.route("/api", methods=["GET"])
def handle_root():
    return cors(jsonify({
        "message": "Digen Image API",
        "endpoints": {
            "generate": "/api/generate?prompt=...&model=flux&mode=sync|async",
            "status": "/api/status?job_id=...&session_id=..."
        },
        "models": list(MODELS.keys()),
    }))


@app.route("/generate", methods=["GET", "OPTIONS"])
@app.route("/api/generate", methods=["GET", "OPTIONS"])
def handle_generate():
    if request.method == "OPTIONS":
        return cors(jsonify({"ok": True}))

    prompt = request.args.get("prompt", "").strip()
    model = request.args.get("model", "flux").strip()
    token = request.args.get("token", "").strip()
    mode = request.args.get("mode", "sync").strip()

    if not prompt:
        return cors(jsonify({"error": "Prompt is required"}), 400)

    try:
        if mode == "async":
            result = submit_only(prompt, model, token or None)
        else:
            result = generate(prompt, model, token or None)
    except Exception as e:
        return cors(jsonify({"error": type(e).__name__ + ": " + str(e)}), 500)

    return cors(jsonify(result), 200 if result.get("success") else 502)


@app.route("/status", methods=["GET", "OPTIONS"])
@app.route("/api/status", methods=["GET", "OPTIONS"])
def handle_status():
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


@app.errorhandler(404)
def not_found(e):
    return cors(jsonify({
        "error": "Not found",
        "available": ["/", "/api", "/generate", "/api/generate",
                      "/status", "/api/status"]
    }), 404)


def cors(response, status_code=200):
    response.status_code = status_code
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
