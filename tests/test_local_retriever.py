from hrag.retrieval.local import LocalRetriever


def test_finds_kannel_daycare():
    r = LocalRetriever()
    hits = r.search("Kannel daycare", k=5)
    assert hits and hits[0].id == "3"
    assert "Kannelpolku" in hits[0].text


def test_empty_query():
    assert LocalRetriever().search("a", k=5) == []


def test_trailing_question_mark_does_not_change_top_hit():
    r = LocalRetriever()
    with_mark = r.search("Missä on Kallion kirjasto?", k=5)
    without_mark = r.search("Missä on Kallion kirjasto", k=5)
    assert with_mark and without_mark
    assert with_mark[0].id == without_mark[0].id == "8215"
