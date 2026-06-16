import os
import json
import uuid
import time
import requests

SCENE_IDS_TO_TRY = ["20", "22", "27", "5", "21"]

MODELS = {
    "flux":        {"model": "flux"},
    "flux2":       {"model": "flux2"},
    "flux2-klein": {"model": "flux2-klein"},
    "zimage":      {"model": "zimage"},
    "sora-image":  {"model": "sora-image"},
    "gpt-image":   {"model": "gpt-image-1.5"},
    "gpt-image2":  {"model": "gpt-image2"},
    "seedream5":   {"model": "seedream5"},
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


def get_scene_info(session_id, base_url, token):
    headers = build_headers(session_id, token)
    try:
        r = requests.post(f"{base_url}/v1/user/scene_info",
                          data="{}", headers=headers, timeout=30)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("errCode") == 0 and "data" in data:
            return data["data"]
        if data.get("errCode") != 0:
            return None
        return data
    except Exception:
        return None


def submit_job(prompt, config, code, session_id, scene_id, base_url, token):
    scene_params = json.dumps({
        "cid": "1",
        "generation_type": "2",
        "model_type": "2",
        "is_public": "1",
        "engine": config["model"],
        "prompt": prompt,
        "code": code,
    })

    body = json.dumps({
        "scene_id": scene_id,
        "model": config["model"],
        "title": prompt[:50],
        "task_type": 1,
        "scene_params": scene_params,
    })

    headers = build_headers(session_id, token)
    try:
        r = requests.post(f"{base_url}/v1/scene/job/submitv1",
                          data=body, headers=headers, timeout=60)
        if r.status_code != 200:
            return {"success": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}

        data = r.json()
        if data.get("errCode") != 0:
            return {"success": False, "error": data.get("errMsg", "API error")}

        d = data.get("data")
        if isinstance(d, str):
            job_id = d
        elif isinstance(d, dict):
            job_id = d.get("queueId") or d.get("id") or d.get("job_id")
        else:
            job_id = None

        if not job_id:
            return {"success": False, "error": f"No job ID. Raw: {json.dumps(data)}"}

        return {"success": True, "jobId": job_id}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def poll_for_result(job_id, session_id, base_url, token, max_attempts=30):
    headers = build_headers(session_id, token)

    for i in range(max_attempts):
        time.sleep(5)

        try:
            r = requests.get(
                f"{base_url}/v1/queue/list?page=0&pageSize=10&status=2",
                headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if data.get("errCode") == 0:
                    items = (data.get("data", {}).get("list")
                             or data.get("data") or [])
                    if isinstance(items, list):
                        for item in items:
                            item_id = str(item.get("id") or item.get("job_id") or "")
                            if item_id == str(job_id):
                                output = (item.get("output")
                                          or item.get("video_url")
                                          or item.get("result"))
                                if output:
                                    return {"success": True, "imageUrl": output}
        except Exception:
            pass

        try:
            r = requests.post(
                f"{base_url}/v1/tools/get_url",
                data=json.dumps({"jobID": job_id}),
                headers={**headers, "Content-Type": "application/json"},
                timeout=30)
            if r.status_code == 200:
                text = r.text.strip().strip('"')
                if text.startswith("http"):
                    return {"success": True, "imageUrl": text}
                try:
                    data = r.json()
                    if isinstance(data, dict):
                        url = (data.get("url") or data.get("data")
                               or data.get("result"))
                        if url and isinstance(url, str) and url.startswith("http"):
                            return {"success": True, "imageUrl": url}
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

    return {"success": False, "error": "Timeout waiting for generation"}


def check_job_status(job_id, session_id, base_url, token):
    """One-shot status check (for async polling)."""
    headers = build_headers(session_id, token)

    try:
        r = requests.get(
            f"{base_url}/v1/queue/list?page=0&pageSize=10&status=2",
            headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            if data.get("errCode") == 0:
                items = (data.get("data", {}).get("list")
                         or data.get("data") or [])
                if isinstance(items, list):
                    for item in items:
                        item_id = str(item.get("id") or item.get("job_id") or "")
                        if item_id == str(job_id):
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
            data=json.dumps({"jobID": job_id}),
            headers={**headers, "Content-Type": "application/json"},
            timeout=30)
        if r.status_code == 200:
            text = r.text.strip().strip('"')
            if text.startswith("http"):
                return {"status": "completed", "image_url": text}
    except Exception:
        pass

    return {"status": "processing"}


def submit_only(prompt, model="flux", token=None, base_url=None):
    """Submit job and return job_id immediately (for async flow)."""
    if not token:
        from config import DIGEN_TOKEN
        token = DIGEN_TOKEN
    if not base_url:
        from config import BASE_URL
        base_url = BASE_URL

    base_url = base_url.rstrip("/")
    model = model.lower()
    config = MODELS.get(model, MODELS["flux"])
    session_id = generate_uuid()

    scene_info = get_scene_info(session_id, base_url, token)
    if not scene_info or not scene_info.get("code"):
        return {"success": False, "error": "Failed to get scene info. Check your token."}

    code = scene_info["code"]

    for scene_id in SCENE_IDS_TO_TRY:
        result = submit_job(prompt, config, code, session_id,
                            scene_id, base_url, token)
        if result["success"]:
            return {
                "success": True,
                "job_id": result["jobId"],
                "session_id": session_id,
                "status": "processing"
            }

    return {"success": False, "error": "All scene IDs failed to submit"}


def generate(prompt, model="flux", token=None, base_url=None):
    """Submit + poll + return (sync flow)."""
    if not token:
        from config import DIGEN_TOKEN
        token = DIGEN_TOKEN
    if not base_url:
        from config import BASE_URL
        base_url = BASE_URL

    base_url = base_url.rstrip("/")
    model = model.lower()
    config = MODELS.get(model, MODELS["flux"])
    session_id = generate_uuid()

    scene_info = get_scene_info(session_id, base_url, token)
    if not scene_info or not scene_info.get("code"):
        return {"success": False, "error": "Failed to get scene info. Check your token."}

    code = scene_info["code"]

    last_error = None
    for scene_id in SCENE_IDS_TO_TRY:
        result = submit_job(prompt, config, code, session_id,
                            scene_id, base_url, token)
        if result["success"]:
            job_id = result["jobId"]
            poll_result = poll_for_result(job_id, session_id, base_url, token)
            if poll_result["success"]:
                image_url = poll_result["imageUrl"]
                return {"success": True, "image_url": image_url}
            last_error = poll_result["error"]
        else:
            last_error = result["error"]

    return {"success": False, "error": f"All scene IDs failed. Last: {last_error}"}
