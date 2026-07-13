from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from pathlib import Path
from pydantic import SecretStr

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

OPENAI_API_KEY = SecretStr(os.getenv("OPENAI_API_KEY") or " ")

llm = ChatOpenAI(
    model="gpt-4o-mini", 
    api_key=OPENAI_API_KEY, 
    temperature=0
)
