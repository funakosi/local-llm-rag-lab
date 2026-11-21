import os
import threading
import webbrowser
from multiprocessing import resource_tracker

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Collapsible,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Log,
    Markdown,
    Select,
    Static,
    Switch,
)

from local_llm_rag_lab.news_rag import search_news
from local_llm_rag_lab.news_rag.question_store import ACTIVE, load_questions, score_answer


class NewsSearchApp(App):
    TITLE = "ニュース RAG"

    CSS = """
    #question { width: 100%; }
    #preset { width: 100%; }
    #options { height: 3; padding: 0 1; }
    #options Switch { margin-right: 1; }
    #options Label { height: 3; content-align: left middle; margin-right: 3; }
    #main { height: 1fr; }
    #answer-box { width: 3fr; border: round $primary; }
    #side { width: 2fr; }
    #articles { height: 40%; border: round $secondary; }
    #detail-box { height: 1fr; border: round $secondary; }
    #log-box { height: auto; max-height: 14; }
    #log { height: 10; }
    #status { height: 1; color: $text-muted; padding: 0 1; }
    """

    BINDINGS = [
        Binding("ctrl+l", "focus_question", "質問入力"),
        Binding("f3", "focus_preset", "登録質問"),
        Binding("ctrl+t", "toggle_mode", "RAG切替"),
        Binding("ctrl+b", "toggle_think", "思考切替"),
        Binding("ctrl+x", "stop_generation", "強制停止"),
        Binding("f2", "toggle_theme", "ライト/ダーク"),
        Binding("o", "open_article", "記事を開く"),
        Binding("ctrl+g", "toggle_log", "ログ表示切替"),
        Binding("ctrl+r", "clear_log", "ログ消去"),
        Binding("ctrl+q", "quit", "終了"),
    ]

    def __init__(self):
        super().__init__()
        self.articles = []
        self.preset = {
            q["question"]: q
            for q in load_questions()
            if q["status"] == ACTIVE
        }
        self.answer_title = "回答"
        self.stop_event = threading.Event()
        self.running = False

    def preset_options(self):
        """data/questions.json の有効な質問を選択肢にする。"""
        return [(question, question) for question in self.preset]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="質問を入力して Enter", id="question")
        yield Select(
            self.preset_options(),
            prompt="登録済みの質問から選択 (F3)",
            id="preset"
        )
        with Horizontal(id="options"):
            yield Switch(value=True, id="rag")
            yield Label("RAGあり(ニュース検索+LLM)", id="rag-label")
            yield Switch(value=True, id="think")
            yield Label("思考あり", id="think-label")
            yield Switch(value=self.theme == "textual-dark", id="dark")
            yield Label("ダークモード", id="dark-label")
        with Horizontal(id="main"):
            with VerticalScroll(id="answer-box"):
                yield Markdown("質問を入力してください。", id="answer")
            with Vertical(id="side"):
                yield ListView(id="articles")
                with VerticalScroll(id="detail-box"):
                    yield Static("", id="detail")
        with Collapsible(title="推論ログ (Ctrl+G で表示切替)", collapsed=False, id="log-box"):
            yield Log(id="log", auto_scroll=True)
        yield Label("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#articles").border_title = "参考記事 (o: ブラウザで開く)"
        self.query_one("#answer-box").border_title = "回答"
        self.query_one("#detail-box").border_title = "記事本文"
        self.query_one("#question").focus()
        self.warm_up()

    @work(thread=True)
    def warm_up(self) -> None:
        """初回検索を待たせないよう、埋め込みモデルを先に読み込む。"""
        self.call_from_thread(self.set_status, "埋め込みモデルを読み込み中...")
        self.call_from_thread(self.write_log, "埋め込みモデルを読み込み中...\n")
        search_news.get_embedding_model()
        self.call_from_thread(self.write_log, "埋め込みモデルの読み込み完了\n")
        self.call_from_thread(self.set_status, "準備完了")

    def write_log(self, text: str) -> None:
        self.query_one("#log", Log).write(text)

    def log_from_thread(self, text: str) -> None:
        self.call_from_thread(self.write_log, text)

    def action_toggle_log(self) -> None:
        box = self.query_one("#log-box", Collapsible)
        box.collapsed = not box.collapsed

    def action_clear_log(self) -> None:
        self.query_one("#log", Log).clear()

    def set_status(self, text: str) -> None:
        self.query_one("#status", Label).update(text)

    def use_rag(self) -> bool:
        return self.query_one("#rag", Switch).value

    def use_think(self) -> bool:
        return self.query_one("#think", Switch).value

    def action_toggle_mode(self) -> None:
        self.query_one("#rag", Switch).toggle()

    def action_toggle_think(self) -> None:
        self.query_one("#think", Switch).toggle()

    def action_stop_generation(self) -> None:
        """推論がループした場合などに、実行中の処理を強制停止する。"""
        if not self.running:
            return
        self.stop_event.set()
        self.set_status("停止中...")
        self.write_log("\n[強制停止を要求しました]\n")

    def action_toggle_theme(self) -> None:
        self.query_one("#dark", Switch).toggle()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "rag":
            label = (
                "RAGあり(ニュース検索+LLM)" if event.value
                else "RAGなし(LLMのみ)"
            )
            self.query_one("#rag-label", Label).update(label)
            self.set_status(f"モード: {'RAGあり' if event.value else 'RAGなし'}")
        elif event.switch.id == "think":
            self.query_one("#think-label", Label).update(
                "思考あり" if event.value else "思考なし"
            )
            self.set_status(f"思考: {'あり' if event.value else 'なし'}")
        elif event.switch.id == "dark":
            self.theme = "textual-dark" if event.value else "textual-light"
            self.query_one("#dark-label", Label).update(
                "ダークモード" if event.value else "ライトモード"
            )

    def action_focus_preset(self) -> None:
        self.query_one("#preset", Select).focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is Select.NULL:
            return
        question = self.query_one("#question", Input)
        question.value = str(event.value)
        question.cursor_position = len(question.value)
        question.focus()
        # 同じ質問を続けて選べるよう、選択状態を戻す。
        event.select.clear()

    def action_focus_question(self) -> None:
        self.query_one("#question").focus()

    def action_open_article(self) -> None:
        index = self.query_one("#articles", ListView).index
        if index is not None and index < len(self.articles):
            url = self.articles[index]["url"]
            if url:
                webbrowser.open(url)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        question = event.value.strip()
        if not question:
            return
        use_rag = self.use_rag()
        think = self.use_think()
        self.answer_title = (
            f"回答 [{'RAGあり' if use_rag else 'RAGなし'}"
            f"/{'思考あり' if think else '思考なし'}]"
        )
        self.query_one("#answer-box").border_title = self.answer_title
        self.query_one("#question").disabled = True
        self.query_one("#answer", Markdown).update("*回答を生成中...*")
        self.query_one("#articles", ListView).clear()
        self.query_one("#detail", Static).update("")
        self.articles = []
        self.write_log(f"\n===== 質問: {question} (RAG: {'有' if use_rag else '無'}, 思考: {'有' if think else '無'}) =====\n")
        self.stop_event.clear()
        self.running = True
        self.run_query(question, use_rag, think, self.preset.get(question))

    @work(thread=True, exclusive=True)
    def run_query(
        self, question: str, use_rag: bool, think: bool, preset: dict | None
    ) -> None:
        try:
            if use_rag:
                self.call_from_thread(self.set_status, "検索中...")
                articles = search_news.search_news(
                    question, on_log=self.log_from_thread
                )
                self.call_from_thread(self.show_articles, articles)
                self.call_from_thread(self.set_status, "LLMで回答を生成中...")
                answer = search_news.generate_answer(
                    question, articles, on_log=self.log_from_thread,
                    think=think, should_stop=self.stop_event.is_set
                )
            else:
                self.call_from_thread(self.set_status, "LLMで回答を生成中...")
                answer = search_news.generate_answer_without_rag(
                    question, on_log=self.log_from_thread, think=think,
                    should_stop=self.stop_event.is_set
                )
        except search_news.GenerationStopped:
            self.call_from_thread(self.write_log, "強制停止しました。\n")
            self.call_from_thread(
                self.show_answer, "*強制停止しました。*", "停止"
            )
            return
        except Exception as e:
            self.call_from_thread(self.write_log, f"エラー: {e}\n")
            self.call_from_thread(self.show_answer, f"**エラー:** {e}", "エラー")
            return

        match = None
        if preset:
            # 登録済みの質問は、期待値との一致度を採点する。
            self.call_from_thread(self.set_status, "期待値との一致度を採点中...")
            try:
                score, comment = score_answer(
                    question, preset["expected_answer"], answer
                )
                match = (score, comment, preset["expected_answer"])
                self.call_from_thread(
                    self.write_log, f"一致度: {score}% ({comment})\n"
                )
            except Exception as e:
                self.call_from_thread(self.write_log, f"採点に失敗: {e}\n")
        self.call_from_thread(self.show_answer, answer, "完了", match)

    def show_articles(self, articles) -> None:
        self.articles = articles
        view = self.query_one("#articles", ListView)
        for article in articles:
            view.append(ListItem(Label(
                f"{article['published_at'][:10]} {article['title']}"
            )))

    def show_answer(self, answer: str, status: str, match=None) -> None:
        box = self.query_one("#answer-box")
        box.border_title = self.answer_title
        if match:
            score, comment, expected = match
            box.border_title = f"{self.answer_title} 期待値との一致度: {score}%"
            answer = (
                f"> **期待値との一致度: {score}%**\n>\n"
                f"> 期待値: {expected}\n>\n"
                f"> 採点: {comment}\n\n---\n\n{answer}"
            )
        self.running = False
        self.query_one("#answer", Markdown).update(answer)
        self.set_status(status)
        question = self.query_one("#question", Input)
        question.disabled = False
        question.focus()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        index = self.query_one("#articles", ListView).index
        if index is None or index >= len(self.articles):
            return
        a = self.articles[index]
        self.query_one("#detail", Static).update(
            f"{a['title']}\n{a['published_at']}\n{a['url']}"
            f"\n距離: {a['distance']:.3f}\n\n{a['text']}"
        )


def main() -> None:
    # Textual は sys.stderr を差し替えるため、起動後に torch 等が
    # resource_tracker を起動すると "bad value(s) in fds_to_keep" になる。
    # 差し替え前に起動しておく。
    resource_tracker.ensure_running()
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    NewsSearchApp().run()


if __name__ == "__main__":
    main()
