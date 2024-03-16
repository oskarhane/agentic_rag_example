import os
from dotenv import load_dotenv
from openai import OpenAI
from llm import LLM

load_dotenv()


class OpenAIAssitant(LLM):
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.open_ai_client = OpenAI(api_key=self.api_key)
        self.model = "gpt-3.5-turbo-0125"
        self.embedding_model = "text-embedding-ada-002"

    def invoke(self, messages, model=None, tools=[], config={}):
        response = self.open_ai_client.chat.completions.create(
            model=model or self.model, messages=messages, tools=tools or None, **config
        )
        return response

    def get_embedding(self, text):
        text = text.replace("\n", " ")
        return (
            self.open_ai_client.embeddings.create(
                input=[text], model=self.embedding_model
            )
            .data[0]
            .embedding
        )
