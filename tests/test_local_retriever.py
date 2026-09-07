from hrag.retrieval.local import LocalRetriever


def test_finds_kannel_daycare():
    r = LocalRetriever()
    hits = r.search("Kannel daycare", k=5)
    assert hits and hits[0].id == "3"
    assert "Kannelpolku" in hits[0].text


def test_empty_query():
    assert LocalRetriever().search("a", k=5) == []
