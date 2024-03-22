from .retriever import Retriever
import json


class PlotVectorRetriever(Retriever):
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
