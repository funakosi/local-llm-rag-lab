"""RAG 評価: 質問に対するチャットボットの回答と正解の類似度を測る。

各質問をナレッジ付きでチャットボットに投げ、回答と正解の埋め込みコサイン類似度、
および出典ファイルが正解の根拠ファイルをどれだけ含むか(再現率)を出力する。
"""

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests

from .client import chat, embed, find_knowledge, list_knowledge
from .config import EMBEDDING_MODEL, MODEL

DEFAULT_QA = "docs/社内文書評価用QA/rag-eval-questions.jsonl"
DEFAULT_KNOWLEDGE = "社内文書サンプル"


def load_qa(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def split_files(value):
    return [v.strip() for v in value.split(";") if v.strip()]


def evaluate_one(qa, knowledge_id):
    result = {
        "id": qa["id"],
        "type": qa.get("type"),
        "difficulty": qa.get("difficulty"),
        "question": qa["question"],
        "reference": qa["answer"],
    }
    expected = split_files(qa.get("evidence_files", ""))
    try:
        answer, sources = chat([{"role": "user", "content": qa["question"]}], knowledge_id)
        ref_vec, ans_vec = embed([qa["answer"], answer])
    except requests.RequestException as e:
        result["error"] = str(e)
        return result
    found = [f for f in expected if f in sources]
    result.update(
        answer=answer,
        similarity=cosine(ref_vec, ans_vec),
        expected_files=expected,
        sources=sources,
        source_recall=len(found) / len(expected) if expected else None,
    )
    return result


def mean(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else float("nan")


def print_summary(results, threshold):
    ok = [r for r in results if "error" not in r]
    errors = len(results) - len(ok)
    print("\n=== 結果 ===")
    print(f"{'ID':<6}{'種別':<12}{'難易度':<8}{'類似度':>7}{'出典再現率':>11}  出典")
    for r in results:
        if "error" in r:
            print(f"{r['id']:<6}{r['type']:<12}{r['difficulty']:<8}  ERROR: {r['error']}")
            continue
        recall = "-" if r["source_recall"] is None else f"{r['source_recall']:.2f}"
        print(
            f"{r['id']:<6}{r['type']:<12}{r['difficulty']:<8}"
            f"{r['similarity']:>7.3f}{recall:>11}  {', '.join(r['sources'])}"
        )

    print("\n=== 集計 ===")
    sims = [r["similarity"] for r in ok]
    print(f"件数: {len(results)} (エラー {errors})")
    if not ok:
        return
    print(f"類似度 平均 {mean(sims):.3f} / 中央値 {statistics.median(sims):.3f} / 最小 {min(sims):.3f}")
    hit = sum(s >= threshold for s in sims)
    print(f"類似度 {threshold} 以上: {hit}/{len(ok)} ({hit / len(ok):.0%})")
    print(f"出典再現率 平均 {mean(r['source_recall'] for r in ok):.3f}")
    for key in ("type", "difficulty"):
        groups = defaultdict(list)
        for r in ok:
            groups[r[key]].append(r)
        print(f"\n[{key}別]")
        for name, rs in sorted(groups.items(), key=lambda kv: str(kv[0])):
            print(
                f"  {name:<12} n={len(rs):<3} 類似度 {mean(r['similarity'] for r in rs):.3f}"
                f"  出典再現率 {mean(r['source_recall'] for r in rs):.3f}"
            )


def main():
    parser = argparse.ArgumentParser(description="RAG 評価(回答と正解の類似度)")
    parser.add_argument("--qa", default=DEFAULT_QA, help=f"QA の jsonl (デフォルト {DEFAULT_QA})")
    parser.add_argument(
        "--knowledge", default=DEFAULT_KNOWLEDGE, metavar="ID|名前",
        help=f"評価するナレッジ (デフォルト {DEFAULT_KNOWLEDGE})",
    )
    parser.add_argument("--no-rag", action="store_true", help="RAG なしで回答させる(ベースライン比較用)")
    parser.add_argument("--ids", nargs="+", metavar="ID", help="指定した ID の質問だけ評価する")
    parser.add_argument("--limit", type=int, help="先頭から N 件だけ評価する")
    parser.add_argument("--threshold", type=float, default=0.8, help="合格とみなす類似度 (デフォルト 0.8)")
    parser.add_argument("--output", help="結果の jsonl の出力先 (デフォルト docs/rag-eval-results-日時.jsonl)")
    args = parser.parse_args()

    qa_list = load_qa(args.qa)
    if args.ids:
        qa_list = [q for q in qa_list if q["id"] in args.ids]
    if args.limit:
        qa_list = qa_list[: args.limit]
    if not qa_list:
        raise SystemExit("評価対象の質問がありません")

    kb = find_knowledge(args.knowledge, list_knowledge())
    if kb is None:
        raise SystemExit(f"ナレッジが見つかりません: {args.knowledge}")
    knowledge_id = None if args.no_rag else kb["id"]

    print(f"モデル: {MODEL} / 埋め込み: {EMBEDDING_MODEL}")
    print(f"ナレッジ: {kb['name']} ({'RAG なし' if args.no_rag else 'RAG あり'}) / 質問数: {len(qa_list)}")

    results = []
    try:
        for i, qa in enumerate(qa_list, 1):
            print(f"[{i}/{len(qa_list)}] {qa['id']} {qa['question']}", file=sys.stderr, flush=True)
            results.append(evaluate_one(qa, knowledge_id))
    except KeyboardInterrupt:
        print(f"\n中断しました。ここまでの {len(results)} 件で集計します", file=sys.stderr)

    if not results:
        raise SystemExit(1)

    print_summary(results, args.threshold)

    output = Path(args.output or f"docs/rag-eval-results-{datetime.now():%Y%m%d-%H%M%S}.jsonl")
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n詳細を保存しました: {output}")


if __name__ == "__main__":
    main()
