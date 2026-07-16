from app.retrieval import reciprocal_rank_fusion


def test_rrf_rewards_documents_present_in_both_rankings():
    vector = [{"_id": "a"}, {"_id": "b"}, {"_id": "c"}]
    lexical = [{"_id": "b"}, {"_id": "d"}, {"_id": "a"}]
    result = reciprocal_rank_fusion([vector, lexical])
    assert result[0]["_id"] == "b"
    assert {item["_id"] for item in result} == {"a", "b", "c", "d"}

