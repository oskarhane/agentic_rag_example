from .retriever import Retriever
import json


class Text2Cypher(Retriever):
    def __init__(self, driver, llm):
        super().__init__()
        self.driver = driver
        self.llm = llm
        self.name = "custom_db_query"

    def invoke(self, question: str, extra_context: str = "") -> str:
        print(f"Text2Cypher invoked: {question}")
        schema_results, _, _ = self.driver.execute_query(
            "CALL apoc.meta.schema()", database="recommendations"
        )

        messages = [
            {
                "role": "system",
                "content": """
                You are an expert at generating correct Cypher queries from user questions and Neo4j schema descriptions. 
                You respond with a Cypher query only. 
                You do not add or assume any information, the response to the question must come as a result of runnig the Cypher query.
                Note that relationships are directional.
                Note that relationships also can have properties.
                Make sure to use DISTINCT when needed.
                """,
            },
            {
                "role": "assistant",
                "content": f"The Neo4j schema description is: {json.dumps(schema_results[0])}",
            },
            {
                "role": "user",
                "content": f"Question to generate Cypher to find the answer: '{question}'. Cypher:",
            },
        ]
        if extra_context:
            messages.insert(
                -2,
                {
                    "role": "assistant",
                    "content": f"Here is some extra context to take into account: '{extra_context}'",
                },
            )
        cypher_response = self.llm.invoke(
            messages, model="ft:gpt-3.5-turbo-0613:neo4j::8G3Cf276"
        )
        cypher = cypher_response.choices[0].message.content
        print(cypher)

        try:
            records, _, _ = self.driver.execute_query(
                cypher, database="recommendations"
            )
        except Exception as e:
            print(f"Error: {e}")
            extra_context = f"""
                The following generated Cypher yielded an error:
                '{cypher}'
                
                The error was: '{e}'

                Make sure you are using this information.
                """
            return self.invoke(question, extra_context)

        return json.dumps([{**record} for record in records])

    def to_tools_dict(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "For questions that require a custom database query. Like counts, sums, recommendations, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The question to find the answer for",
                        }
                    },
                    "required": ["question"],
                },
            },
        }
