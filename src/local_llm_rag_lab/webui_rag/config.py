from dotenv import dotenv_values, find_dotenv

config = dotenv_values(find_dotenv(usecwd=True) or find_dotenv())

BASE_URL = config.get("OPENWEBUI_URL", "http://localhost:3000")
API_KEY = config["OPENWEBUI_API_KEY"]
MODEL = config.get("OPENWEBUI_MODEL", "qwen3.6:35b-a3b")
EMBEDDING_MODEL = config.get("OPENWEBUI_EMBEDDING_MODEL", "bge-m3:latest")
KNOWLEDGE_ID = config.get("OPENWEBUI_KNOWLEDGE_ID")  # 任意: RAG用(デフォルトのナレッジ)
