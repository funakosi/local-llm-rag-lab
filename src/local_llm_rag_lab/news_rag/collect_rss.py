import hashlib
import sqlite3
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import requests

# 主要なニュースに変更
RSS_URL = [
    "https://news.yahoo.co.jp/rss/categories/domestic.xml",
    "https://news.yahoo.co.jp/rss/categories/world.xml",
    "https://news.yahoo.co.jp/rss/categories/business.xml",
    "https://news.yahoo.co.jp/rss/categories/entertainment.xml",
    "https://news.yahoo.co.jp/rss/categories/sports.xml",
    "https://news.yahoo.co.jp/rss/topics/it.xml",
    "https://news.yahoo.co.jp/rss/categories/science.xml",
    "https://news.yahoo.co.jp/rss/categories/life.xml",
    "https://news.yahoo.co.jp/rss/topics/local.xml"
]
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "news.db"


def parse_datetime(value):
    """RSSの日時をISO 8601形式に変換する。"""
    if not value:
        return None

    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def init_db():
    """SQLiteのテーブルを作成する。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                article_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                published_at TEXT,
                summary TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            )
        """)


def collect_rss():
    """RSSのリストから記事を取得し、SQLiteに保存する。"""
    headers = {
        "User-Agent": "OkinawaNewsRAG/1.0"
    }

    entries = []

    for rss_url in RSS_URL:
        try:
            response = requests.get(
                rss_url,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"取得に失敗しました: {rss_url} ({e})")
            continue

        feed = feedparser.parse(response.content)
        entries.extend(feed.entries)

    if not entries:
        print("記事が見つかりませんでした。")
        return

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated = 0

    with sqlite3.connect(DB_PATH) as conn:
        for entry in entries:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            summary = entry.get("summary", "").strip()
            published_at = parse_datetime(
                entry.get("published")
                or entry.get("updated")
            )

            if not title or not url:
                continue

            # URLを基に記事IDを作成する。
            article_id = hashlib.sha256(
                url.encode("utf-8")
            ).hexdigest()

            existing = conn.execute(
                """
                SELECT title, summary, published_at
                FROM articles
                WHERE article_id = ?
                """,
                (article_id,)
            ).fetchone()

            conn.execute(
                """
                INSERT INTO articles (
                    article_id,
                    title,
                    url,
                    published_at,
                    summary,
                    first_seen_at,
                    last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(article_id) DO UPDATE SET
                    title = excluded.title,
                    published_at = excluded.published_at,
                    summary = excluded.summary,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    article_id,
                    title,
                    url,
                    published_at,
                    summary,
                    now,
                    now
                )
            )

            if existing is None:
                inserted += 1
            elif existing != (title, summary, published_at):
                updated += 1

    print(f"新規登録: {inserted} 件")
    print(f"既存記事の更新: {updated} 件")
    print(f"RSS掲載記事数: {len(entries)} 件")

def main() -> None:
    init_db()
    collect_rss()

if __name__ == "__main__":
    main()
