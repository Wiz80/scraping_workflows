# app/helpers/queue_manager.py

import json
import os
from typing import List, Dict

JSON_QUEUES_PATH = "app/cache/queues.json"

def load_queues() -> Dict:
    if not os.path.exists(JSON_QUEUES_PATH):
        return {"queues": []}
    with open(JSON_QUEUES_PATH, "r") as f:
        return json.load(f)

def save_queues(data: Dict):
    with open(JSON_QUEUES_PATH, "w") as f:
        json.dump(data, f, indent=4)

def add_queue(base_url: str, queue_name: str, pending_urls: List[str] = None):
    data = load_queues()
    if not any(queue["queue_name"] == queue_name for queue in data["queues"]):
        data["queues"].append({
            "base_url": base_url,
            "queue_name": queue_name,
            "status": "active",
            "pending_urls": pending_urls.copy() if pending_urls else [],
            "last_processed_url": None
        })
    save_queues(data)

def update_queue_status(queue_name: str, status: str):
    data = load_queues()
    for queue in data["queues"]:
        if queue["queue_name"] == queue_name:
            queue["status"] = status
            break
    save_queues(data)

def remove_queue(queue_name: str):
    data = load_queues()
    data["queues"] = [queue for queue in data["queues"] if queue["queue_name"] != queue_name]
    save_queues(data)

def remove_pending_url(queue_name: str, url: str):
    data = load_queues()
    for queue in data["queues"]:
        if queue["queue_name"] == queue_name:
            if url in queue["pending_urls"]:
                queue["pending_urls"].remove(url)
            break
    save_queues(data)

def add_pending_url(queue_name: str, url: str):
    data = load_queues()
    for queue in data["queues"]:
        if queue["queue_name"] == queue_name:
            if url not in queue["pending_urls"]:
                queue["pending_urls"].append(url)
            break
    save_queues(data)

def get_pending_urls(queue_name: str) -> List[str]:
    data = load_queues()
    for queue in data["queues"]:
        if queue["queue_name"] == queue_name:
            return queue.get("pending_urls", [])
    return []

def get_all_queues() -> List[Dict]:
    data = load_queues()
    return data.get("queues", [])