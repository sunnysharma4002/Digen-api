import os
import sys
import json

# Ensure parent dir is on path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from digen_image_api import generate

app = Flask(__name__)


@app.route("/api/generate", methods=["GET", "POST", "OPTIONS"])
def handle_generate():
    if request.method == "OPTIONS":
        return cors_response(jsonify({"ok": True}))

    prompt = (request.args.get("prompt")
              or (request.json or {}).get("prompt")
              or "").strip()
    model = (request.args.get("model")
             or (request.json or {}).get("model")
             or "flux").strip()
    token = (request.args.get("token")
             or (request.json or {}).get("token")
             or "").strip()

    if not prompt:
        return cors_response(jsonify({"error": "Prompt is required"}), 400)

    result = generate(prompt, model, token if token else None)

    resp = jsonify(result)
    return cors_response(resp, 200 if result.get("success") else 502)


@app.route("/api", methods=["GET"])
def handle_root():
    return cors_response(jsonify({
        "message": "Digen Image API",
        "usage": "GET /api/generate?prompt=...&model=flux",
        "models": ["flux", "flux2", "flux2-klein", "zimage",
                   "sora-image", "gpt-image", "gpt-image2", "seedream5"],
    }))


def cors_response(response, status_code=200):
    response.status_code = status_code
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# Vercel handler
handler = app
