import json
import os

def get_supervisor_openid():
    try:
        with open("data/supervisor.json", "r") as f:
            supervisor_openid = json.load(f).get("supervisor_openid")
        return supervisor_openid
    except FileNotFoundError:
        return None


def set_supervisor_openid(supervisor_openid):
    os.makedirs("data", exist_ok=True)
    with open("data/supervisor.json", "w") as f:
        json.dump({"supervisor_openid": supervisor_openid}, f)


def get_item(file_path, key):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(key)
    except FileNotFoundError:
        return None