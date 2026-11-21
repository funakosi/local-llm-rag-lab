# ニュース記事をソースとしたRAGアプリ

## 事前設定

- ollamaをインストール
  - [0401_ollama.md参照](0401_ollama.md)
  - 動作させるPCによってはモデルがロードできない場合があるので、適宜モデルを変更する
- リポジトリを取得
```bash
$ git clone https://github.com/funakosi/local-llm-rag-lab.git
$ cd local-llm-rag-lab
$ uv sync
```

## 使い方

```bash
# yahooニュースのrssフィードからデータを取得
# data/news.db に保存される
$ uv run news-collect

# 取得したデータからベクトルDBを作成
# data/chroma_db に保存される
$ uv run news-build-vecdb

# 取得したデータから質問を作成(TUI用)
$ uv run python -m local_llm_rag_lab.news_rag.generate_questions

# 検索実行(CUI)
$ uv run news-cui
# 検索実行(TUI)
$ uv run news-tui
```
