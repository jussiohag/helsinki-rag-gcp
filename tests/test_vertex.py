from hrag.retrieval.vertex import VertexSearchRetriever


class FakeDoc:
    def __init__(self, doc_id: str, struct_data: dict) -> None:
        self.id = doc_id
        self.struct_data = struct_data


class FakeResult:
    def __init__(self, doc_id: str, struct_data: dict, relevance_score: float) -> None:
        self.document = FakeDoc(doc_id, struct_data)
        self.relevance_score = relevance_score


class FakeSearchClient:
    def __init__(self, results: list[FakeResult]) -> None:
        self.results = results
        self.last_request: dict | None = None

    def search(self, request: dict) -> list[FakeResult]:
        self.last_request = request
        return self.results


def test_search_maps_results_to_passages():
    results = [
        FakeResult("1", {"name": "Kannel Library", "content": "Kannelpolku 6", "url": "https://x/1"}, 0.9),
        FakeResult("2", {"name": "Malmi Library", "content": "Malmi 2", "url": "https://x/2"}, 0.5),
    ]
    client = FakeSearchClient(results)
    retriever = VertexSearchRetriever(client=client, serving_config="projects/p/servingConfigs/default")

    passages = retriever.search("library", k=5)

    assert [p.id for p in passages] == ["1", "2"]
    assert passages[0].title == "Kannel Library"
    assert passages[0].text == "Kannelpolku 6"
    assert passages[0].source_url == "https://x/1"
    assert passages[0].score == 0.9
    assert client.last_request is not None
    assert client.last_request["serving_config"] == "projects/p/servingConfigs/default"
    assert client.last_request["query"] == "library"


def test_search_respects_k():
    results = [FakeResult(str(i), {"name": f"n{i}", "content": "", "url": ""}, 0.0) for i in range(10)]
    client = FakeSearchClient(results)
    retriever = VertexSearchRetriever(client=client)

    passages = retriever.search("q", k=3)

    assert len(passages) == 3


def test_search_handles_missing_struct_data():
    client = FakeSearchClient([FakeResult("1", {}, 0.0)])
    retriever = VertexSearchRetriever(client=client)

    passages = retriever.search("q", k=5)

    assert passages[0].id == "1"
    assert passages[0].title == ""
    assert passages[0].text == ""
