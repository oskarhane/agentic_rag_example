from retrievers.retriever import Retriever
from retrievers.agentic_retriever import AgenticRetriever
from llm import LLM
import json


class RetrieverRouter(Retriever):
    def __init__(self, llm: LLM, retrievers: list[AgenticRetriever]) -> None:
        self.llm = llm
        self.retrievers = retrievers
        pass

    def invoke(self, input: str) -> str:
        return json.dumps(self.handle_input(input))

    def handle_input(self, input: str) -> list[dict[str, str]]:
        tools = [retriever.to_tools_dict() for retriever in self.retrievers]
        print(json.dumps(tools))

        # Break up the input into stand alone questions
        questions = self.query_expansion(input)
        print(f"Expanded questions: {questions}")

        # Route the questions to the right tools and get answers
        output = self.route_questions(questions, tools)

        # Critique the responses and see if they need to be expanded
        unanswered_questions = self.critique_responses(input, output)
        print(f"Unanswered questions: {unanswered_questions}")
        if len(unanswered_questions):
            output = self.route_questions(unanswered_questions, tools, output)

        return output

    def route_questions(
        self, questions, tools, output: list[dict[str, str]] = []
    ) -> list[dict[str, str]]:
        tool_picker_prompt = """
            Your job is to chose the right tool needed to respond to the user question. 
            The available tools are provided to you in the prompt.
            Make sure to pass the right and complete arguments to the chosen tool.
            """
        system_message = {
            "role": "system",
            "content": tool_picker_prompt,
        }
        answers = []

        while len(questions):
            question = questions.pop(0)
            updated_question = self.update_question(question, output)
            print(f"Updated question: {updated_question}")
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
                    "content": f"For the question '{question}', we have answers: {json.dumps(tools_output)}",
                }
            )
            output.append({"question": question, "answers": tools_output})
        return output

    def handle_tool_calls(self, tool_calls):
        output = []
        if tool_calls:
            available_functions = {}
            for strategy in self.retrievers:
                available_functions[strategy.name] = strategy.invoke
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                res = function_to_call(**function_args)
                output.append(res)
        return output

    def critique_responses(
        self, input: str, responses: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        messages = [
            {
                "role": "system",
                "content": """
                You are an expert at identifying if questions has been fully answered or if there is an opportunity to expand the answer.
                The user will provide a question, and you will scan through the provided information to see if there is anything missing.
                If anything is missing, you will provide a set of new questions that can be asked to gather the missing information.
                All new questions must be atomic and specific.
                If the information is complete, you will provide an empty list.

                JSON template to use for finding missing information:
                {
                    "questions": ["question1", "question2"]
                }
                """,
            },
            {
                "role": "assistant",
                "content": f"The information gathered to answer the original user question: {json.dumps(responses)}",
            },
            {
                "role": "user",
                "content": f"The original user question to answer: {input}",
            },
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

    def query_expansion(self, input: str) -> list[str]:
        query_expansion_prompt = """
            You are an expert in langage and understanding semantic meaning.
            You read input from person and your job is to expand the input
            into stand alone atomic questions.

            You must return JSON using the template below.

            Example:
            Input: Who is Mick Jagger and how old is he?
            Output: 
            {
                "questions": [
                    "Who is Mick Jagger?",
                    "How old is Mick Jagger?"
                ]
            }
            """
        messages = [
            {"role": "system", "content": query_expansion_prompt},
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
                You are an expert at updating questions with context to make the original question more atomic, specific and easier to find the answer for.
                You respond with the updated question that has all information in it.
                Only edit the question if needed. If the original question already is atomic, specific and easy to answer, you keep the original.
                Ask for one thing only in the new question, or you will be terminated.
             
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
