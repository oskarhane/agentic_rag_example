from retriever import Retriever


class AnswerInContext(Retriever):
    def __init__(self):
        super().__init__()
        self.name = "extract_answer_from_context"

    def search(self, answer: str) -> str:
        print(f"AnswerInContext invoked: {answer}")
        return answer

    def to_tools_dict(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "If a complete and satisfactionary answer to the question already is provided in context, use this tool.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string",
                            "description": "The answer to the question",
                        }
                    },
                    "required": ["answer"],
                },
            },
        }
