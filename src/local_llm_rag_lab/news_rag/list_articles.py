import argparse
import os
import sqlite3
import sys
from pathlib import Path


SQLITE_PATH = Path(__file__).resolve().parents[2] / "data" / "news.db"


def main():
    parser = argparse.ArgumentParser(description="記事のタイトルと概要を一覧表示する")
    parser.add_argument("-n", "--limit", type=int, help="表示件数の上限")
    args = parser.parse_args()

    query = """
        SELECT title, summary
        FROM articles
        ORDER BY published_at DESC
    """
    params = ()
    if args.limit:
        query += " LIMIT ?"
        params = (args.limit,)

    with sqlite3.connect(SQLITE_PATH) as conn:
        rows = conn.execute(query, params).fetchall()

    for i, (title, summary) in enumerate(rows, 1):
        print(f"[{i}] {title}")
        print(f"    {summary or '(概要なし)'}")
        print()


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # less などが先に終了した場合は静かに終える。
        # 終了時のflushで再度エラーにならないよう出力先を差し替える。
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
