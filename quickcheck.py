# quickcheck.py
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()
client = AzureOpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    api_version=os.environ["OPENAI_API_VERSION"],
    azure_endpoint=os.environ["OPENAI_API_BASE"],
)

print(
    "Chat:",
    client.chat.completions.create(
        model=os.environ["CHAT_DEPLOYMENT"],
        messages=[{"role":"user","content":"ping"}],
        temperature=0.0
    ).choices[0].message.content
)

print(
    "Emb len:",
    len(
        client.embeddings.create(
            model=os.environ["EMBEDDING_DEPLOYMENT"],
            input="ping"
        ).data[0].embedding
    )
)
