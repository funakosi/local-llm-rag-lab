import argparse
import itertools
import readline  # noqa: F401  input() の行編集(日本語のバックスペース等)を有効にする
import sys
import threading
from contextlib import contextmanager

from .client import chat, find_knowledge, list_knowledge
from .config import KNOWLEDGE_ID


@contextmanager
def thinking(label="考え中"):
    """応答待ちの間、スピナーを表示する(TTY のときのみ)。"""
    if not sys.stderr.isatty():
        yield
        return
    stop = threading.Event()

    def spin():
        for frame in itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
            if stop.wait(0.08):
                break
            sys.stderr.write(f"\r{frame} {label}...")
            sys.stderr.flush()

    t = threading.Thread(target=spin, daemon=True)
    sys.stderr.write("\033[?25l")  # カーソルを隠す
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join()
        sys.stderr.write("\r\033[K\033[?25h")  # 行を消してカーソルを戻す
        sys.stderr.flush()


def select_knowledge(knowledge_list):
    """番号入力でナレッジを選ぶ。キャンセルや無効な入力は None。"""
    if not knowledge_list:
        print("ナレッジがありません")
        return None
    for n, kb in enumerate(knowledge_list, 1):
        print(f"  {n}. {kb['name']}  ({kb['id']})")
    try:
        choice = input("番号> ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(knowledge_list):
        return knowledge_list[int(choice) - 1]
    print("選択をキャンセルしました")
    return None


def format_answer(answer, sources):
    if not sources:
        return answer
    return answer + "\n\n出典: " + ", ".join(sources)


def main():
    parser = argparse.ArgumentParser(description="Open WebUI chat")
    parser.add_argument("message", nargs="*", help="質問(省略すると対話モード)")
    parser.add_argument("--no-rag", action="store_true", help="RAG(ナレッジ参照)を使わない")
    parser.add_argument("--knowledge", metavar="ID|名前", help="使用するナレッジ(ID または名前)")
    parser.add_argument("--list-knowledge", action="store_true", help="ナレッジ一覧を表示して終了")
    args = parser.parse_args()

    knowledge_list = list_knowledge()

    if args.list_knowledge:
        for kb in knowledge_list:
            print(f"{kb['name']}\t{kb['id']}")
        return

    # 使用するナレッジ: --knowledge > .env の OPENWEBUI_KNOWLEDGE_ID
    kb = None
    key = args.knowledge or KNOWLEDGE_ID
    if key:
        kb = find_knowledge(key, knowledge_list)
        if kb is None:
            if args.knowledge:
                raise SystemExit(f"ナレッジが見つかりません: {args.knowledge}")
            kb = {"id": key, "name": key}  # 一覧に無くても .env の ID はそのまま使う
    use_rag = kb is not None and not args.no_rag

    history = []
    if args.message:
        history.append({"role": "user", "content": " ".join(args.message)})
        try:
            with thinking():
                answer, sources = chat(history, kb["id"] if use_rag else None)
        except KeyboardInterrupt:
            raise SystemExit(130)
        print(format_answer(answer, sources))
        return

    def status():
        if use_rag:
            return f"RAG: ON ({kb['name']})"
        return "RAG: OFF"

    print(f"{status()}  (/rag で ON/OFF、/kb でナレッジ選択)")
    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            continue
        if q == "/rag":
            if kb is None:
                print("ナレッジが未選択です。/kb で選択してください\n")
                continue
            use_rag = not use_rag
            print(f"{status()}\n")
            continue
        if q == "/kb":
            knowledge_list = list_knowledge()
            chosen = select_knowledge(knowledge_list)
            if chosen:
                kb, use_rag = chosen, True
            print(f"{status()}\n")
            continue
        history.append({"role": "user", "content": q})
        try:
            with thinking():
                a, sources = chat(history, kb["id"] if use_rag else None)
        except KeyboardInterrupt:
            history.pop()  # 中断した質問は履歴から取り消す
            print("(中断しました)\n")
            continue
        history.append({"role": "assistant", "content": a})
        print(f"bot> {format_answer(a, sources)}\n")


if __name__ == "__main__":
    main()
