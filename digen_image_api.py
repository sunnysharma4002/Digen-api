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

# set at module level after _load_config
_token = None
_base_url = None


def generate_uuid():
    return str(uuid.uuid4())


def build_headers(session_id, token, content_type="application/json"):
    return {
        "Content-Type": content_type,
        "Digen-Language": "en",
        "Digen-SessionID": session_id,
        "Digen-Token": token,
    }


def submit_job(prompt, model, token, base_url, session_id):
    body = json.dumps({"model": model, "prompt": prompt})
    headers = build_headers(session_id, token)

    try:
        r = requests.post(f"{base_url}/v1/scene/job/submitv1",
                          data=body, headers=headers, timeout=60)
        if r.status_code != 200:
            return {"success": False, "error": f"HTTP {r.status_code}"}

        data = r.json()
        if data.get("errCode") != 0:
            return {"success": False, "error": data.get("errMsg", "API error")}

        d = data.get("data")
        if isinstance(d, str):
            if d.startswith("http"):
                return {"success": True, "url": d}
            return {"success": True, "queueId": str(d)}

        if isinstance(d, dict):
            url = (d.get("url") or d.get("image_url")
                   or d.get("output") or d.get("result")
                   or d.get("imgUrl"))
            if url:
                return {"success": True, "url": url}
            qid = d.get("queueId") or d.get("id") or d.get("job_id")
            if qid:
                return {"success": True, "queueId": str(qid)}

        url = (data.get("url") or data.get("image_url")
               or data.get("output") or data.get("result"))
        if url:
            return {"success": True, "url": url}

        return {"success": False, "error": f"Unexpected response: {json.dumps(data)}"}

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def poll_for_result(queue_id, session_id, token, base_url, max_attempts=30):
    headers = {"Content-Type": "application/json",
               "Digen-Language": "en",
               "Digen-SessionID": session_id}

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
                            if item_id == queue_id:
                                output = (item.get("output")
                                          or item.get("video_url")
                                          or item.get("result"))
                                if output:
                                    return {"success": True, "imageUrl": output}

            r2 = requests.post(
                f"{base_url}/v1/tools/get_url",
                data=json.dumps({"jobID": queue_id}),
                headers={**headers, "Digen-Token": token},
                timeout=30)
            if r2.status_code == 200:
                text = r2.text.strip().strip('"')
                if text.startswith("http"):
                    return {"success": True, "imageUrl": text}
                try:
                    data2 = r2.json()
                    if isinstance(data2, dict):
                        url = (data2.get("url") or data2.get("data")
                               or data2.get("result"))
                        if url and isinstance(url, str) and url.startswith("http"):
                            return {"success": True, "imageUrl": url}
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

    return {"success": False, "error": "Timeout waiting for generation"}


def check_job_status(queue_id, session_id, token, base_url):
    headers = {"Content-Type": "application/json",
               "Digen-Language": "en",
               "Digen-SessionID": session_id}

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
                        if item_id == queue_id:
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
            data=json.dumps({"jobID": queue_id}),
            headers={**headers, "Digen-Token": token},
            timeout=30)
        if r.status_code == 200:
            text = r.text.strip().strip('"')
            if text.startswith("http"):
                return {"status": "completed", "image_url": text}
    except Exception:
        pass

    return {"status": "processing"}


def _load_config():
    global _token, _base_url
    _token = os.environ.get("DIGEN_TOKEN")
    _base_url = os.environ.get("BASE_URL", "https://api.digen.ai")
    if not _token:
        try:
            from config import DIGEN_TOKEN, BASE_URL
            _token = DIGEN_TOKEN
            _base_url = BASE_URL
        except ImportError:
            pass
    return _token, _base_url


def submit_only(prompt, model="flux", token=None, base_url=None):
    _token_local, _base_url_local = _load_config()
    token = token or _token_local
    base_url = (base_url or _base_url_local).rstrip("/")

    if not token:
        return {"success": False, "error": "DIGEN_TOKEN not configured"}

    model_val = MODELS.get(model.lower(), MODELS["flux"])
    session_id = generate_uuid()

    result = submit_job(prompt, model_val, token, base_url, session_id)
    if not result["success"]:
        return result

    if "url" in result:
        return {"success": True, "image_url": result["url"], "session_id": session_id}

    return {
        "success": True,
        "job_id": result["queueId"],
        "session_id": session_id,
        "status": "processing"
    }


def generate(prompt, model="flux", token=None, base_url=None):
    _token_local, _base_url_local = _load_config()
    token = token or _token_local
    base_url = (base_url or _base_url_local).rstrip("/")

    if not token:
        return {"success": False, "error": "DIGEN_TOKEN not configured"}

    model_val = MODELS.get(model.lower(), MODELS["flux"])
    session_id = generate_uuid()

    result = submit_job(prompt, model_val, token, base_url, session_id)
    if not result["success"]:
        return result

    if "url" in result:
        return {"success": True, "image_url": result["url"]}

    queue_id = result["queueId"]
    poll_result = poll_for_result(queue_id, session_id, token, base_url)
    return poll_result
