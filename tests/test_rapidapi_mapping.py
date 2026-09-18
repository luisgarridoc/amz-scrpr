"""Test unitario puro (sin red) del mapeo de /best-sellers y /search al
esquema interno.

Fixtures basadas en respuestas reales de la API "Real-Time Amazon Data"
(categoría "electronics" y búsqueda "padel racket").
"""
from scouting.rapidapi_client import (
    _parse_price,
    map_best_sellers_to_products,
    map_search_to_products,
)

SAMPLE_RESPONSE = {
    "status": "OK",
    "data": {
        "best_sellers": [
            {
                "rank": 1,
                "asin": "B08JHCVHTY",
                "product_title": "blink plus plan with monthly auto-renewal",
                "product_price": "$11.99",
                "product_star_rating": "4.4",
                "product_num_ratings": 280277,
            },
            {
                "rank": 44,
                "asin": "B0GR1493ZV",
                "product_title": "Apple 2026 MacBook Air 13-inch",
                "product_price": "$1,249.00",
                "product_star_rating": "4.7",
                "product_num_ratings": 1110,
            },
            {
                "rank": 28,
                "asin": "B0DN45YMP6",
                "product_title": "JBL Vibe Beam 2",
                "product_price": None,
                "product_star_rating": "4.1",
                "product_num_ratings": 7085,
            },
        ]
    },
}


def test_map_best_sellers_parses_price_and_thousands_separator():
    products = map_best_sellers_to_products(SAMPLE_RESPONSE)
    by_asin = {p["asin"]: p for p in products}

    assert by_asin["B08JHCVHTY"]["price"] == 11.99
    assert by_asin["B0GR1493ZV"]["price"] == 1249.00
    assert by_asin["B08JHCVHTY"]["bsr"] == 1
    assert by_asin["B08JHCVHTY"]["reviews"] == 280277


def test_map_best_sellers_skips_items_without_price():
    products = map_best_sellers_to_products(SAMPLE_RESPONSE)
    asins = {p["asin"] for p in products}
    assert "B0DN45YMP6" not in asins
    assert len(products) == 2


def test_parse_price_handles_us_and_european_formats():
    assert _parse_price("$1,249.00") == 1249.00
    assert _parse_price("$11.99") == 11.99
    assert _parse_price("49,90 €") == 49.90
    assert _parse_price("1.249,00 €") == 1249.00
    assert _parse_price(None) is None
    assert _parse_price("") is None


SAMPLE_SEARCH_RESPONSE = {
    "status": "OK",
    "data": {
        "products": [
            {
                "asin": "B0FKH5HZXJ",
                "product_title": "Bullpadel Game PWR Gris",
                "product_price": "$99.95",
                "product_num_ratings": 32,
            },
            {
                "asin": "B0GL8KF89G",
                "product_title": "Raquette de Padel para Principiantes",
                "product_price": None,
                "product_num_ratings": 10,
            },
        ]
    },
}


def test_map_search_to_products_skips_missing_price_and_has_no_bsr():
    products = map_search_to_products(SAMPLE_SEARCH_RESPONSE)
    assert len(products) == 1
    assert products[0]["asin"] == "B0FKH5HZXJ"
    assert products[0]["price"] == 99.95
    assert products[0]["bsr"] is None
