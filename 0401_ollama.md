# Ollama

## インストール

ollamaをインストールして、モデルを起動する。
```bash
$ brew install ollama
$ ollama --version
$ ollama run <model_name>
```

サービスとしてollamaを起動しておくと便利
```bash
$ brew services start ollama
```

```bash
$ ollama ls
NAME               ID              SIZE      MODIFIED
gemma3:27b         6be2e2ba6843    17 GB     11 days ago
bge-m3:latest      790764642607    1.2 GB    6 weeks ago
qwen3.6:35b-a3b    a7eb95c53bcf    22 GB     7 weeks ago
```

## 使い方

### チャット

```bash
% ollama run qwen3.6:35b-a3b
>>> AIエージェントとは何？

# AI エージェント（AI Agent）とは？

**AI エージェント**とは、人工知能（AI）を活用し、環境を感知・解釈して自律的に判断・行動し、特定の目標を達成するソフト
ウェアプログラムのことです。

従来の AI が「与えられた質問に答える」ことに特化していたのに対し、AI エージェントは「目的を持って計画を立て、ツールを
使い、反復的に課題を解決する」点に大きな違いがあります。

（途中省略）

📖 **参考リンク**
- OpenAI の Agent Framework: https://platform.openai.com/docs/guides/function-calling
- LangChain / CrewAI / AutoGPT などのオープンソース実装例
- Microsoft Research: "Generative AI Agents" (2023)
- IEEE Standard for AI System Design and Implementation

特定の分野や技術実装についてさらに詳しく知りたい場合は、お気軽にお知らせください。
```

### 要約

青空文庫から「走れメロス」のテキストを取得し、UTF8に変換しておく。
```bash
$ wget https://www.aozora.gr.jp/cards/000035/files/1567_ruby_4948.zip
$ unzip 1567_ruby_4948.zip
$ nkf -w --overwrite hashire_merosu.txt
```

```bash
$ ollama run qwen3.6:35b-a3b \
> "このテキストの内容を200文字で要約して" \
> < hashire_merosu.txt

暴君暗殺を狙った牧人メロスは、死刑延期の条件に友人を人質として妹の結婚式へ向かう。約束通り帰還するため、豪雨や川、山賊を乗り越えつつ、極限の疲労と自己疑念にも直面するが、友への絶対的信任和誠を糧に走破した。刑場到着寸前で友人を救い出し、その信実が暴君の心も打ち砕き王は改心する。人の信頼と誠実の偉大さを描いた作品である。
```



