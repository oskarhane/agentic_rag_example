from strategy import Strategy
import json


class PlotVectorStrategy(Strategy):
    def __init__(self, driver, llm):
        super().__init__()
        self.driver = driver
        self.llm = llm
        self.name = "get_movie_by_plot"
        # self.index_name = "moviePlotsEmbedding"
        # self.retrieval_query = """
        #     WITH node, score
        #     MATCH (node)-[r:ACTED_IN]->(a:Actor)
        #     WITH node, score, collect({name: a.name, roles: r.roles}) as actors
        #     RETURN {movie: {title: node.title, plot: node.plot}, actors: actors} AS result, score
        # """

    def invoke(self, plot: str) -> str:
        print(f"VectorStrategy invoked: {plot}")
        # plot_embedding = self.llm.get_embedding(plot)
        # print(plot_embedding)
        # q = f"""
        #     CALL db.index.vector.queryNodes('{self.index_name}', $k, $plot_embedding) YIELD node, score
        #     {self.retrieval_query}
        # """
        # print(q)
        # records, _, _ = self.driver.execute_query(
        #     q, plot_embedding=plot_embedding, k=2, database="recommendations"
        # )
        q = """
            MATCH (m:Movie) WHERE toLower(m.plot) CONTAINS toLower($plot) RETURN m {.title, .plot, .year} as result LIMIT 1
        """
        records, _, _ = self.driver.execute_query(
            q, plot=plot, database="recommendations"
        )
        if records:
            return json.dumps({"movie": {**records[0]["result"]}})
        return "No movie found for the plot"

    def to_tools_dict(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Matches movie taglines / stories to a user's input, and returns information about the movie.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plot": {
                            "type": "string",
                            "description": "The plot / story / tagline of the movie",
                        }
                    },
                    "required": ["plot"],
                },
            },
        }


class MovieStrategy(Strategy):
    def __init__(self, driver):
        super().__init__()
        self.name = "get_movie_from_name"
        self.driver = driver

    def invoke(self, title: str, match_type: str) -> str:
        print(f"MovieStrategy invoked: '{title}' '{match_type}'")
        if match_type == "exact":
            match_str = "m.title = $title"
        else:
            match_str = "m.title CONTAINS $title"
        q = f"""
            MATCH (m:Movie)<-[r:ACTED_IN]-(a:Actor) 
            WHERE {match_str} 
            WITH m, collect({{name: a.name, role: r.role}}) as actors
            RETURN m {{.title, .plot, .year}} AS movie, actors 
            LIMIT 1
        """

        records, _, _ = self.driver.execute_query(
            q, title=title, database="recommendations"
        )

        if records:
            return json.dumps([{**record} for record in records])
        return "No plot found for the movie"

    def to_tools_dict(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Get movie details by providing the movie title. Returns actors and plot.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The title of the movie",
                        },
                        "match_type": {
                            "type": "string",
                            "enum": ["exact", "contains"],
                            "description": "The match type to use",
                        },
                    },
                    "required": ["title", "match_type"],
                },
            },
        }


class Text2Cypher(Strategy):
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
