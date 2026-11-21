import requests

from .config import API_KEY, BASE_URL, EMBEDDING_MODEL, MODEL


def _headers():
    return {"Authorization": f"Bearer {API_KEY}"}


def list_knowledge():
    """既存のナレッジ一覧を [{"id": ..., "name": ...}, ...] で返す。"""
    r = requests.get(f"{BASE_URL}/api/v1/knowledge/", headers=_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    items = data["items"] if isinstance(data, dict) else data
    return [{"id": i["id"], "name": i.get("name", "")} for i in items]


def find_knowledge(key, knowledge_list):
    """ID または名前(完全一致)でナレッジを探す。見つからなければ None。"""
    for kb in knowledge_list:
        if key in (kb["id"], kb["name"]):
            return kb
    return None


def chat(messages, knowledge_id=None):
    """回答と出典ファイル名のリストを返す。"""
    payload = {"model": MODEL, "messages": messages}
    if knowledge_id:
        payload["files"] = [{"type": "collection", "id": knowledge_id}]
    r = requests.post(
        f"{BASE_URL}/api/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"], extract_sources(data)


def extract_sources(data):
    """レスポンスの sources から、重複を除いた出典ファイル名を順に返す。"""
    names = []
    for src in data.get("sources", []):
        for meta in src.get("metadata", []):
            name = meta.get("name") or meta.get("source")
            if name and name not in names:
                names.append(name)
    return names


def embed(texts):
    """テキストのリストを埋め込みベクトルのリストに変換する。"""
    r = requests.post(
        f"{BASE_URL}/api/embeddings",
        headers=_headers(),
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=120,
    )
    r.raise_for_status()
    data = sorted(r.json()["data"], key=lambda d: d.get("index", 0))
    return [d["embedding"] for d in data]
