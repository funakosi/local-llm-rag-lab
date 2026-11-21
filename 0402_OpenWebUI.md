# OpenWebUI

## インストール

```bash
# Docker Desktopをインストール
$ brew install --cask docker
```

compose.yml
```yml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    ports:
      - "3000:8080"
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    volumes:
      - open-webui:/app/backend/data
    restart: unless-stopped

volumes:
  open-webui:
```

```bash
$ docker compose -f compose.yml up
```

## 設定

### 1.インフラ設定

- ポート: `3000:8080`
- `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- データ: 名前付きボリューム `open-webui` → `/app/backend/data`(webui.db / uploads / vector_db を含む)

### 2.管理者設定
初期値からの変更点

#### 認証・一般

| 項目                                 | 設定値   | 初期値   |
| ---------------------------------- | ----- | ----- |
| APIキーの有効化 (`auth.enable_api_keys`) | true  | false |
| 新規サインアップ (`ui.enable_signup`)      | false | true  |
  
#### 接続

| 項目     | 設定値 |
| ------ | ------- |
| Ollama | 有効 / `http://host.docker.internal:11434` |
| OpenAI | 有効 / `https://api.openai.com/v1` / Bearer認証 / API種別: `responses` / APIキー: 設定済み(**値は本ファイルに記載せず。別途安全に保管**) |

#### ドキュメント(RAG)

| 項目   | 設定値  | 初期値  |
| ----- | ------ | ------ |
| 埋め込みエンジン (`rag.embedding_engine`)   | ollama   | (内蔵)  |
| 埋め込みモデル (`rag.embedding_model`)   | `bge-m3:latest` |  sentence-transformers/all-MiniLM-L6-v2 |
| ハイブリッド検索 (`rag.enable_hybrid_search`) | 有効  | 無効  |
| リランキングモデル (`rag.reranking_model`)    | `BAAI/bge-reranker-v2-m3` | (なし) |
| チャンクサイズ (`rag.chunk_size`)   | 200 | 1000  |
| チャンクオーバーラップ (`rag.chunk_overlap`) | 20  | 100  |
| Top K (`rag.top_k`)   | 5   | 3   |

#### 3.カスタムモデル

| 項目  | 内容   |
|----- | ------ |
| ID  |`qwen3635b-a3b-nothink`  |
| 表示名   | `qwen3.6:35b-a3b-nothink`   |
| ベースモデル  | `qwen3.6:35b-a3b`(Ollama)    |
| 詳細パラメータ | カスタムパラメータ `chat_template_kwargs` = `{"enable_thinking": false}`(思考モードOFF)  |
| 機能 | 初期値のまま(vision / file_upload / web_search / code_interpreter / citations / memory / builtin_tools 等すべて有効) |
| システムプロンプト・ナレッジ紐付け | なし    |
| ユーザー既定モデル  | `qwen3.6:35b-a3b`  |


## 4. ナレッジ(ドキュメント)

### 女生徒(説明: サンプル)

- `joseito.txt`(約92KB, text/plain)

### 社内文書サンプル(説明: サンプルの文書で問い合わせテスト)

| ファイル            | サイズ(byte) |
| ------------------ | --------- |
| 01-pc-kitei.md     | 5,902     |
| 02-vpn-tejun.md    | 3,296     |
| 03-account.md      | 4,197     |
| 04-shinsei.md      | 3,657     |
| 05-incident.md     | 3,321     |
| 06-faq.md          | 5,822     |
| 07-pc-kitei-kyu.md | 1,580     |
| 08-kishu-hyo.md    | 2,514     |
| 09-giji-2026-05.md | 4,309     |


## 使い方

ブラウザから以下のURLにアクセスする
```
http://localhost:3000/
```
もしくはサーバを起動している端末のIPアドレスを指定する
```
http://<サーバのIPアドレス>:3000/
```


