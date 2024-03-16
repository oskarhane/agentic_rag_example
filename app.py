from strategy import Strategy
from llm import LLM
from app_prompts import query_expansion, tool_picker, response_generation
import json


class RagApp:
    def __init__(self, llm: LLM) -> None:
        self.llm = llm
        self.strategies = []
        pass

    def load_strategy(self, strategy: Strategy) -> None:
        self.strategies.append(strategy)

    def handle_input(self, input: str) -> None:
        output = []
        tools = [strategy.to_tools_dict() for strategy in self.strategies]
        print(json.dumps(tools))
        # 1. Break up the input into stand alone questions
        questions = self.query_expansion(input)
        print(f"Expanded questions: {questions}")
        # 2. Loop through the questions and let the LLM decide
        # which strategy to use per question
        system_message = {
            "role": "system",
            "content": tool_picker,
        }
        answers = []
        # TODO: Add task list that can be updated by responses from the tools
        # it's limitied by the original number of questions at the moment
        # Need event loop and scoped(do we need concurrency?) queue to handle this
        for question in questions:
            updated_questions = [self.update_question(question, output)]
            print(f"Updated question: {updated_questions}")
            for updated_question in updated_questions:
                llm_response = self.llm.invoke(
                    [
                        system_message,
                        *answers,
                        {
                            "role": "user",
                            "content": f"The user question to find a tool to get the answer with: '{updated_question}'",
                        },
                    ],
                    tools=tools,
                )
                tools_choices = llm_response.choices[0].message

                tools_output = self.handle_tool_calls(tools_choices.tool_calls)
                print(f"Response from tools: {tools_output}")
                answers.append(
                    {
                        "role": "assistant",
                        "content": f"For the question '{question}', we have already found answers: {json.dumps(tools_output)}",
                    }
                )
                output.append({"question": question, "answers": tools_output})
        return self.generate_response(input, output)

    def handle_tool_calls(self, tool_calls):
        output = []
        if tool_calls:
            available_functions = {}
            for strategy in self.strategies:
                available_functions[strategy.name] = strategy.invoke
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                res = function_to_call(**function_args)
                output.append(res)
        return output

    def generate_response(self, input: str, output):
        response = self.llm.invoke(
            messages=[
                {"role": "system", "content": response_generation},
                {
                    "role": "assistant",
                    "content": f"""This is the information you must use: {json.dumps(output)}""",
                },
                {
                    "role": "user",
                    "content": f"The original user question to answer: {input}",
                },
            ]
        )
        return response.choices[0].message.content

    def query_expansion(self, input: str) -> str:
        messages = [
            {"role": "system", "content": query_expansion},
            {"role": "user", "content": f"The user question to expand: '{input}'"},
        ]
        config = {
            "response_format": {"type": "json_object"},
        }
        output = self.llm.invoke(messages, config=config)
        try:
            return json.loads(output.choices[0].message.content)["questions"]
        except json.JSONDecodeError:
            print("Error decoding JSON")
        return []

    def update_question(self, question: str, context: str) -> str:
        messages = [
            {
                "role": "system",
                "content": """
                You are an expert at updating questions with context to make the original question more atomic, specific and easier to answer.
                You respond with the updated question that has all information in it.
                But you only edit the question if needed. If it already is atomic, specific and easy to answer, you keep the original.


             
                JSON template to use:
                {
                    "question": "question1"
                }
             """,
            },
            {
                "role": "assistant",
                "content": f"The context you can use to make the question atomic is: '{context}'",
            },
            {"role": "user", "content": f"The user question to expand: '{question}'"},
        ]

        config = {
            "response_format": {"type": "json_object"},
        }
        output = self.llm.invoke(messages, config=config)
        try:
            return json.loads(output.choices[0].message.content)["question"]
        except json.JSONDecodeError:
            print("Error decoding JSON")
        return []
