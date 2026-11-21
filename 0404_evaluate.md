# OpenWebUIで構築したRAGを評価

## 事前設定

- ollamaをインストール
  - [0401_ollama.md参照](0401_ollama.md)
  - 動作させるPCによってはモデルがロードできない場合があるので、適宜モデルを変更する
- OpenWebUIをインストール
  - インストールや設定内容については以下を参照
  - [0402_OpenWebUI.md参照](0402_OpenWebUI.md)

- リポジトリを取得
```bash
$ git clone https://github.com/funakosi/local-llm-rag-lab.git
$ cd local-llm-rag-lab
$ uv sync
```

- プロジェクト直下に`.env`ファイルを追加して、以下の項目を登録しておく
```
OPENWEBUI_API_KEY={OpenAIのAPIキーを記載}
OPENWEBUI_URL=http://localhost:3000
OPENWEBUI_MODEL={デフォルトのモデルを指定}
OPENWEBUI_KNOWLEDGE_ID={デフォルトのナレッジIDを指定}
```

ナレッジIDについては以下の手順で取得できる。
- OpenWebUI > ワークスペース > ナレッジベース
- タイトルを指定 > 画面右上にIDが表示されるので、それを指定する

## 使い方

### チャット

```bash
$ uv run webui-chat
```

- /rag でragの有無を切り替えられる
- /kb でナレッジを選択できる

### 評価

```bash
uv run webui-eval
```

オプション
```bash
$ uv run webui-eval --help
usage: webui-eval [-h] [--qa QA] [--knowledge ID|名前] [--no-rag] [--ids ID [ID ...]] [--limit LIMIT] [--threshold THRESHOLD] [--output OUTPUT]

RAG 評価(回答と正解の類似度)

options:
  -h, --help            show this help message and exit
  --qa QA               QA の jsonl (デフォルト docs/rag-eval-questions.jsonl)
  --knowledge ID|名前     評価するナレッジ (デフォルト 社内文書サンプル)
  --no-rag              RAG なしで回答させる(ベースライン比較用)
  --ids ID [ID ...]     指定した ID の質問だけ評価する
  --limit LIMIT         先頭から N 件だけ評価する
  --threshold THRESHOLD
                        合格とみなす類似度 (デフォルト 0.8)
  --output OUTPUT       結果の jsonl の出力先 (デフォルト docs/rag-eval-results-日時.jsonl)
```

先頭の3件だけを指定して評価する
```bash
$ uv run webui-eval --limit 3
モデル: qwen3.6:35b-a3b / 埋め込み: bge-m3:latest
ナレッジ: 社内文書サンプル (RAG あり) / 質問数: 3
[1/3] Q001 会社貸与PCの標準更新周期は何年ですか？
[2/3] Q002 VPN接続時に選択する接続先名は何ですか？
[3/3] Q003 セキュリティ事故またはその疑いを認識した場合、何分以内にどこへ第一報を行いますか？

=== 結果 ===
ID    種別          難易度         類似度      出典再現率  出典
Q001  single_file easy      0.815       0.00  07-pc-kitei-kyu.md, 09-giji-2026-05.md, 04-shinsei.md
Q002  single_file easy      0.754       1.00  02-vpn-tejun.md, 06-faq.md, 07-pc-kitei-kyu.md, 03-account.md
Q003  single_file easy      0.950       1.00  05-incident.md, 03-account.md, 01-pc-kitei.md

=== 集計 ===
件数: 3 (エラー 0)
類似度 平均 0.840 / 中央値 0.815 / 最小 0.754
類似度 0.8 以上: 2/3 (67%)
出典再現率 平均 0.667

[type別]
  single_file  n=3   類似度 0.840  出典再現率 0.667

[difficulty別]
  easy         n=3   類似度 0.840  出典再現率 0.667

詳細を保存しました: docs/rag-eval-results-20261121-162539.jsonl
```
