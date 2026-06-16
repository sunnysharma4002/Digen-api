import os
import json
import uuid
import time
import requests

MODELS = {
    "flux":        "flux",
    "flux2":       "flux2",
    "flux2-klein": "flux2-klein",
    "zimage":      "zimage",
    "sora-image":  "sora-image",
    "gpt-image":   "gpt-image-1.5",
    "gpt-image2":  "gpt-image2",
    "seedream5":   "seedream5",
}

SCENE_ID = "20"
TASK_TYPE = 1


def generate_uuid():
    return str(uuid.uuid4())


def get_code(session_id, token, base_url):
    """Get per-session code from scene_info endpoint."""
    headers = {
        "Content-Type": "application/json",
        "Digen-Language": "en",
        "Digen-SessionID": session_id,
        "Digen-Token": token,
    }
    try:
        r = requests.post(f"{base_url}/v1/user/scene_info",
                          json={}, headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if data.get("errCode") == 0:
                return data.get("data", {}).get("code", "")
    except Exception:
        pass
    return None


def build_body(prompt, model_val, code):
    """Build the full request body for image generation."""
    scene_params = json.dumps({
        "cid": "1",
        "generation_type": "2",
        "model_type": "2",
        "is_public": "1",
        "engine": model_val,
        "prompt": prompt,
        "code": code,
    })
    return json.dumps({
        "scene_id": SCENE_ID,
        "model": model_val,
        "title": prompt[:50],
        "task_type": TASK_TYPE,
        "scene_params": scene_params,
    })


def submit_job(prompt, model_val, session_id, token, base_url):
    """Submit image generation job, return queueId or error."""
    code = get_code(session_id, token, base_url)
    if not code:
        return {"success": False, "error": "Failed to get scene code"}

    body = build_body(prompt, model_val, code)
    headers = {
        "Content-Type": "application/json",
        "Digen-Language": "en",
        "Digen-SessionID": session_id,
        "Digen-Token": token,
    }

    try:
        r = requests.post(f"{base_url}/v1/scene/job/submitv1",
                          data=body, headers=headers, timeout=60)
        if r.status_code != 200:
            return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}

        data = r.json()
        ec = data.get("errCode")
        if ec != 0:
            return {"success": False, "error": data.get("errMsg", f"API error {ec}")}

        qid = data.get("data", {}).get("queueId", "")
        if not qid:
            return {"success": False, "error": f"No queueId in response: {r.text[:200]}"}

        return {"success": True, "queueId": str(qid)}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def poll_result(queue_id, session_id, token, base_url, max_attempts=30):
    """Poll for completed job with image URL."""
    headers_poll = {
        "Content-Type": "application/json",
        "Digen-Language": "en",
        "Digen-SessionID": session_id,
        "Digen-Token": token,
    }

    for i in range(max_attempts):
        time.sleep(5)

        try:
            r = requests.get(
                f"{base_url}/v1/queue/list?page=0&pageSize=50&status=2",
                headers=headers_poll, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if data.get("errCode") == 0:
                    items = data.get("data", {}).get("list", [])
                    for item in items:
                        iid = str(item.get("id", ""))
                        if iid == queue_id:
                            output = (item.get("output")
                                      or item.get("video_url")
                                      or item.get("result"))
                            if output:
                                return {"success": True, "imageUrl": output}

            r2 = requests.post(
                f"{base_url}/v1/tools/get_url",
                json={"jobID": queue_id},
                headers=headers_poll, timeout=30)
            if r2.status_code == 200:
                text = r2.text.strip().strip('"')
                if text.startswith("http"):
                    return {"success": True, "imageUrl": text}
        except Exception:
            pass

    return {"success": False, "error": "Timeout waiting for generation"}


def check_job_status(queue_id, session_id, token, base_url):
    """One-shot status check for async polling."""
    headers = {
        "Content-Type": "application/json",
        "Digen-Language": "en",
        "Digen-SessionID": session_id,
        "Digen-Token": token,
    }

    try:
        r = requests.get(
            f"{base_url}/v1/queue/list?page=0&pageSize=50&status=2",
            headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if data.get("errCode") == 0:
                items = data.get("data", {}).get("list", [])
                for item in items:
                    iid = str(item.get("id", ""))
                    if iid == queue_id:
                        output = (item.get("output")
                                  or item.get("video_url")
                                  or item.get("result"))
                        if output:
                            return {"status": "completed", "image_url": output}
    except Exception:
        pass

    try:
        r = requests.post(
            f"{base_url}/v1/tools/get_url",
            json={"jobID": queue_id},
            headers=headers, timeout=30)
        if r.status_code == 200:
            text = r.text.strip().strip('"')
            if text.startswith("http"):
                return {"status": "completed", "image_url": text}
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
    """Submit job, return queueId immediately (async)."""
    _token, _base_url = _load_config()
    token = token or _token
    base_url = (base_url or _base_url).rstrip("/")

    if not token:
        return {"success": False, "error": "DIGEN_TOKEN required"}

    model_val = MODELS.get(model.lower())
    if not model_val:
        return {"success": False, "error": f"Unknown model: {model}"}

    session_id = generate_uuid()
    result = submit_job(prompt, model_val, session_id, token, base_url)
    if not result["success"]:
        return result

    return {
        "success": True,
        "job_id": result["queueId"],
        "session_id": session_id,
        "status": "processing"
    }


def generate(prompt, model="flux", token=None, base_url=None):
    """Submit + poll (sync)."""
    _token, _base_url = _load_config()
    token = token or _token
    base_url = (base_url or _base_url).rstrip("/")

    if not token:
        return {"success": False, "error": "DIGEN_TOKEN required"}

    model_val = MODELS.get(model.lower())
    if not model_val:
        return {"success": False, "error": f"Unknown model: {model}"}

    session_id = generate_uuid()
    result = submit_job(prompt, model_val, session_id, token, base_url)
    if not result["success"]:
        return result

    queue_id = result["queueId"]
    poll_result = poll_result(queue_id, session_id, token, base_url)
    return poll_result
