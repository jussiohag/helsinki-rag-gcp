from hrag.generator import GeminiGenerator, TemplateGenerator
from hrag.ports import Passage


def _passages() -> list[Passage]:
    return [
        Passage(id="1", title="Kannel Library", text="Kannelpolku 6. Phone 09-123.", source_url="", score=3),
        Passage(id="2", title="Malmi Library", text="Malmi 2. Phone 09-456.", source_url="", score=2),
        Passage(id="3", title="Itis Library", text="Itis 3. Phone 09-789.", source_url="", score=1),
        Passage(id="4", title="Extra Library", text="Extra 4. Phone 09-000.", source_url="", score=0),
    ]


def test_template_generator_no_answer_when_no_passages():
    answer = TemplateGenerator().generate("Where is the library?", [])
    assert answer.no_answer
    assert answer.citations == ()
    assert answer.model == "template"


def test_template_generator_cites_top_three():
    answer = TemplateGenerator().generate("library?", _passages())
    assert not answer.no_answer
    assert answer.citations == ("1", "2", "3")
    assert "Kannel Library" in answer.text
    assert "[1]" in answer.text
    assert "Extra Library" not in answer.text


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeClient:
    def __init__(self, text: str) -> None:
        self.text = text
        self.last_prompt: str | None = None

    def generate_content(self, prompt: str) -> FakeResponse:
        self.last_prompt = prompt
        return FakeResponse(self.text)


def test_gemini_generator_no_answer_when_no_passages():
    client = FakeClient("irrelevant")
    answer = GeminiGenerator(client=client).generate("q", [])
    assert answer.no_answer
    assert client.last_prompt is None


def test_gemini_generator_parses_known_citations_and_prompt_shape():
    client = FakeClient("The library is at Kannelpolku 6 [1].")
    passages = _passages()
    answer = GeminiGenerator(client=client).generate("Where is the library?", passages)
    assert answer.citations == ("1",)
    assert not answer.no_answer
    assert client.last_prompt is not None
    assert '<passage id="1">' in client.last_prompt
    assert "Where is the library?" in client.last_prompt


def test_gemini_generator_drops_unknown_citations():
    client = FakeClient("See [1] and [999].")
    answer = GeminiGenerator(client=client).generate("q", _passages())
    assert answer.citations == ("1",)


def test_gemini_generator_default_model_name():
    generator = GeminiGenerator(client=FakeClient("x"))
    assert generator.model_name == "gemini-2.5-flash"
