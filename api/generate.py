import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify
from digen_image_api import generate, submit_only

app = Flask(__name__)


@app.route("/", methods=["GET", "POST", "OPTIONS"])
def handle():
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


def cors(response, status_code=200):
    response.status_code = status_code
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
