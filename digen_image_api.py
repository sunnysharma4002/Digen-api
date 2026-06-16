import os
import json
import uuid
import time
import requests

MODELS = {
    "flux":              {"model": "flux", "batch_size": 4},
    "flux2":             {"model": "flux2", "batch_size": 1},
    "flux2-klein":       {"model": "flux2-klein", "batch_size": 4},
    "flux-schnell":      {"model": "black-forest-labs/FLUX.1-schnell", "batch_size": 1},
    "zimage":            {"model": "zimage", "batch_size": 2},
    "sora-image":        {"model": "sora-image", "batch_size": 1},
    "gpt-image":         {"model": "gpt-image-1.5", "batch_size": 1},
    "gpt-image2":        {"model": "gpt-image2", "batch_size": 1},
    "seedream5":         {"model": "seedream5", "batch_size": 5},
    "nano-banana":       {"model": "nano_banana1", "batch_size": 1},
    "nano-banana2":      {"model": "nano_banana2", "batch_size": 1},
    "nano-banana2-r":    {"model": "nano_banana2_r", "batch_size": 1},
    "image-motion":      {"model": "image_motion", "batch_size": 1},
}


def generate_uuid():
    return str(uuid.uuid4())


def build_headers(session_id, token):
    return {
        "Content-Type": "application/json",
        "Digen-Language": "en",
        "Digen-SessionID": session_id,
        "Digen-Token": token,
    }


def submit_job(prompt, model_config, session_id, token, base_url):
    """Submit image generation job to /v2/tools/images_generations."""
    cfg = {
        "model": model_config["model"],
        "prompt": prompt,
        "image_size": "1024x1024",
        "width": 1024,
        "height": 1024,
        "batch_size": model_config["batch_size"],
        "strength": 0.9,
    }

    headers = build_headers(session_id, token)
    try:
        r = requests.post(f"{base_url}/v2/tools/images_generations",
                          json=cfg, headers=headers, timeout=60)
        if r.status_code != 200:
            return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}

        data = r.json()
        if data.get("errCode") != 0:
            return {"success": False, "error": data.get("errMsg", f"API error {data.get('errCode')}")}

        d = data.get("data", {})
        task_id = d.get("id") or d.get("itemId") or ""
        if not task_id:
            return {"success": False, "error": f"No task id in response: {r.text[:200]}"}

        return {"success": True, "taskId": str(task_id)}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def poll_result(task_id, session_id, token, base_url, max_attempts=120):
    """Poll for result using /v6/video/get_task_v2."""
    headers = build_headers(session_id, token)

    for i in range(max_attempts):
        time.sleep(5)

        try:
            r = requests.post(f"{base_url}/v6/video/get_task_v2",
                              json={"jobId": task_id},
                              headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if data.get("errCode") != 0:
                    continue

                d = data.get("data", {})
                status = d.get("status")

                if status == 3:  # SUCCESS
                    urls = d.get("resource_urls", [])
                    if urls:
                        return {"success": True, "imageUrl": urls[0]}
                elif status == 4:  # FAILED
                    return {"success": False, "error": "Generation failed"}
        except Exception:
            pass

    return {"success": False, "error": "Timeout waiting for generation"}


def check_job_status(task_id, session_id, token, base_url):
    """One-shot status check for async polling."""
    headers = build_headers(session_id, token)
    try:
        r = requests.post(f"{base_url}/v6/video/get_task_v2",
                          json={"jobId": task_id},
                          headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if data.get("errCode") == 0:
                d = data.get("data", {})
                status = d.get("status")
                if status == 3:
                    urls = d.get("resource_urls", [])
                    if urls:
                        return {"status": "completed", "image_url": urls[0]}
                elif status == 4:
                    return {"status": "failed", "error": "Generation failed"}
                return {"status": "processing"}
    except Exception:
        pass
    return {"status": "processing"}


def _load_config():
    token = os.environ.get("DIGEN_TOKEN")
    base_url = os.environ.get("BASE_URL", "https://api.digen.ai")
    if not token:
        try:
            from config import DIGEN_TOKEN, BASE_URL
            token = DIGEN_TOKEN
            base_url = BASE_URL
        except ImportError:
            pass
    return token, base_url


def submit_only(prompt, model="flux", token=None, base_url=None):
    """Submit image job, return taskId immediately (async)."""
    _token, _base_url = _load_config()
    token = token or _token
    base_url = (base_url or _base_url).rstrip("/")

    if not token:
        return {"success": False, "error": "DIGEN_TOKEN required"}

    model_config = MODELS.get(model.lower())
    if not model_config:
        return {"success": False, "error": f"Unknown model: {model}"}

    session_id = generate_uuid()
    result = submit_job(prompt, model_config, session_id, token, base_url)
    if not result["success"]:
        return result

    return {
        "success": True,
        "job_id": result["taskId"],
        "session_id": session_id,
        "status": "processing"
    }


def generate(prompt, model="flux", token=None, base_url=None):
    """Submit image and poll for result (sync)."""
    _token, _base_url = _load_config()
    token = token or _token
    base_url = (base_url or _base_url).rstrip("/")

    if not token:
        return {"success": False, "error": "DIGEN_TOKEN required"}

    model_config = MODELS.get(model.lower())
    if not model_config:
        return {"success": False, "error": f"Unknown model: {model}"}

    session_id = generate_uuid()
    result = submit_job(prompt, model_config, session_id, token, base_url)
    if not result["success"]:
        return result

    return poll_result(result["taskId"], session_id, token, base_url)
