import json
from retrievers.retriever import Retriever
from llm import LLM


class Neo4jRAG:
    def __init__(self, llm: LLM, retriever: Retriever) -> None:
        self.llm = llm
        self.retriever = retriever
        pass

    def handle_input(self, input: str) -> str:
        context = self.retriever.invoke(input)
        return self.generate_response(input, context)

    def generate_response(self, input: str, context: str) -> str:
        response_generation_prompt = """
            You are an expoert at formatting useful responses to user questions, using 
            only the information provided by the prompt. You must not use any implicit knowledge.

            If the answer to the question is not provided to you in the prompt,
            let the user know that the information is missing.

            """
        response = self.llm.invoke(
            messages=[
                {"role": "system", "content": response_generation_prompt},
                {
                    "role": "assistant",
                    "content": f"""This is the information you must use: {context}""",
                },
                {
                    "role": "user",
                    "content": f"The original user question to answer: {input}",
                },
            ]
        )
        return response.choices[0].message.content
