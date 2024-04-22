from retriever import Retriever
import json


class MovieRetriever(Retriever):
    def __init__(self, driver):
        super().__init__()
        self.name = "get_movie_from_name"
        self.driver = driver

    def search(self, title: str, match_type: str) -> str:
        print(f"MovieRetriever invoked: '{title}' '{match_type}'")
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
                "description": "Get movie details by providing the full or parts of the movie title.",
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
