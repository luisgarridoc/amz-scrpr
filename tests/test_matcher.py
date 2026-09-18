"""Test unitario puro (sin red) de matching/matcher.py: lógica de selección
del mejor candidato entre los validados por Claude, usando clientes falsos
(duck-typed) en vez de llamadas reales a CJ/Anthropic.
"""
from matching.matcher import find_best_match


class FakeClaude:
    def __init__(self, variants, valid_titles):
        self._variants = variants
        self._valid_titles = set(valid_titles)

    def generate_search_variants(self, amazon_title, n=3):
        return self._variants

    def validate_match(self, amazon_title, cj_title):
        return cj_title in self._valid_titles


class FakeCJ:
    def __init__(self, responses_by_variant):
        self._responses = responses_by_variant

    def search_products(self, keyword, page_size=5):
        return self._responses.get(keyword, {"data": {"list": []}})


def _cj_item(pid, title, price, free_shipping=False):
    return {
        "pid": pid,
        "productNameEn": title,
        "sellPrice": str(price),
        "isFreeShipping": free_shipping,
    }


def test_find_best_match_picks_cheapest_among_validated():
    responses = {
        "neck massager": {
            "data": {
                "list": [
                    _cj_item("p1", "Mini Neck Massager USB", 12.0),
                    _cj_item("p2", "Unrelated Phone Case", 3.0),
                ]
            }
        },
        "portable massager": {
            "data": {"list": [_cj_item("p3", "Portable Neck Massager", 9.5, free_shipping=True)]}
        },
    }
    claude = FakeClaude(
        variants=["neck massager", "portable massager"],
        valid_titles={"Mini Neck Massager USB", "Portable Neck Massager"},
    )
    cj = FakeCJ(responses)

    result = find_best_match("Mini portable neck massager", claude, cj)

    assert result is not None
    assert result["producto_cj"] == "Portable Neck Massager"
    assert result["precio_cj"] == 9.5
    assert result["envio_estimado"] == 0.0  # free shipping


def test_find_best_match_returns_none_if_no_candidate_validates():
    responses = {"keyword": {"data": {"list": [_cj_item("p1", "Totally Unrelated Item", 5.0)]}}}
    claude = FakeClaude(variants=["keyword"], valid_titles=set())
    cj = FakeCJ(responses)

    assert find_best_match("Some Amazon Product", claude, cj) is None


def test_find_best_match_returns_none_if_no_candidates_found():
    claude = FakeClaude(variants=["nada"], valid_titles=set())
    cj = FakeCJ({})

    assert find_best_match("Some Amazon Product", claude, cj) is None
