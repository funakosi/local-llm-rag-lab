import hashlib
import sqlite3
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SQLITE_PATH = DATA_DIR / "news.db"
CHROMA_PATH = DATA_DIR / "chroma_db"
COLLECTION_NAME = "yahoo_news"

MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)


def main():
    # SQLiteから記事を取得する。
    with sqlite3.connect(SQLITE_PATH) as conn:
        rows = conn.execute("""
            SELECT
                article_id,
                title,
                url,
                published_at,
                summary
            FROM articles
            ORDER BY published_at DESC
        """).fetchall()

    if not rows:
        print("SQLiteに記事がありません。")
        return

    # Embeddingモデルを読み込む。
    model = SentenceTransformer(MODEL_NAME)

    # ChromaDBを永続化モードで開く。
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    ids = []
    documents = []
    metadatas = []

    for article_id, title, url, published_at, summary in rows:
        # タイトルと概要を検索対象にする。
        text = f"タイトル: {title}\n概要: {summary or ''}"

        # テキストの変更を検知するためのハッシュ。
        text_hash = hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()

        ids.append(article_id)
        documents.append(text)

        metadatas.append({
            "title": title,
            "url": url,
            "published_at": published_at or "",
            "text_hash": text_hash
        })

    # 既存データと照合し、変更のあった記事だけを処理する。
    existing = collection.get(
        ids=ids,
        include=["metadatas"]
    )

    existing_hashes = {
        article_id: metadata.get("text_hash", "")
        for article_id, metadata in zip(
            existing["ids"],
            existing["metadatas"]
        )
    }

    changed = [
        i for i, article_id in enumerate(ids)
        if existing_hashes.get(article_id)
        != metadatas[i]["text_hash"]
    ]

    if not changed:
        print("ベクトル化が必要な記事はありません。")
        return

    changed_docs = [documents[i] for i in changed]
    changed_ids = [ids[i] for i in changed]
    changed_metadata = [metadatas[i] for i in changed]

    embeddings = model.encode(
        changed_docs,
        normalize_embeddings=True
    ).tolist()

    collection.upsert(
        ids=changed_ids,
        documents=changed_docs,
        metadatas=changed_metadata,
        embeddings=embeddings
    )

    print(f"処理対象の記事数: {len(changed)}")
    print(f"ChromaDBの登録件数: {collection.count()}")


if __name__ == "__main__":
    main()
