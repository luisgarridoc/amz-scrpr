"""Orquestador del pipeline (v1: solo research de gaps de precio).

En TEST_MODE (default) usa scouting/sample_data.py como fuente de productos
Amazon y NO llama a ninguna API externa. Con TEST_MODE=false hace scouting
real vía RapidAPI y matching real vía Claude + CJdropshipping.
"""
from calc.gap_calculator import calculate_gap
from common.cache import MatchingCache
from common.config import settings
from common.logging_conf import get_logger
from output.csv_writer import write_results
from scouting.sample_data import SAMPLE_AMAZON_PRODUCTS

logger = get_logger("main")

# Envío estimado por defecto cuando CJ no lo desglosa en la búsqueda inicial.
DEFAULT_ENVIO_ESTIMADO = 3.0


def run_scouting() -> list[dict]:
    if settings.test_mode:
        logger.info("Usando SAMPLE_AMAZON_PRODUCTS (%d productos) en TEST_MODE", len(SAMPLE_AMAZON_PRODUCTS))
        return SAMPLE_AMAZON_PRODUCTS

    if settings.scouting_source != "rapidapi":
        raise NotImplementedError(
            f"SCOUTING_SOURCE={settings.scouting_source!r} aún no conectado al orquestador "
            "(solo 'rapidapi' está implementado)."
        )

    from scouting.rapidapi_client import (
        RapidAPIAmazonClient,
        map_best_sellers_to_products,
        map_search_to_products,
    )

    client = RapidAPIAmazonClient()

    if settings.scouting_mode == "search":
        if not settings.scouting_keyword:
            raise ValueError("SCOUTING_MODE=search requiere SCOUTING_KEYWORD en .env")
        raw = client.search_products(settings.scouting_keyword, country=settings.scouting_country)
        products = map_search_to_products(raw)
        logger.info(
            "Scouting real: %d productos con precio válido para keyword=%r (país=%s)",
            len(products),
            settings.scouting_keyword,
            settings.scouting_country,
        )
    elif settings.scouting_mode == "best_sellers":
        raw = client.get_best_sellers(settings.scouting_category, country=settings.scouting_country)
        products = map_best_sellers_to_products(raw)
        logger.info(
            "Scouting real: %d productos con precio válido en categoría=%s (país=%s)",
            len(products),
            settings.scouting_category,
            settings.scouting_country,
        )
    else:
        raise NotImplementedError(f"SCOUTING_MODE={settings.scouting_mode!r} no reconocido")

    return products


def run_matching(amazon_product: dict, cache: MatchingCache, claude_client=None, cj_client=None) -> dict | None:
    """Encuentra el equivalente de CJ para un producto de Amazon, cacheado por ASIN.

    En TEST_MODE no llama a Claude/CJ (no hay clientes reales que pasar).
    """
    cache_key = f"asin:{amazon_product['asin']}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached["match"] if cached.get("found") else None

    if settings.test_mode:
        logger.info("TEST_MODE: sin match real de CJ para %s (placeholder)", amazon_product["asin"])
        return None

    from matching.matcher import find_best_match

    match = find_best_match(amazon_product["title"], claude_client, cj_client)
    cache.set(cache_key, {"found": match is not None, "match": match})
    return match


def main() -> None:
    cache = MatchingCache()
    amazon_products = run_scouting()

    if len(amazon_products) > settings.max_products_per_run:
        logger.info(
            "Limitando a MAX_PRODUCTS_PER_RUN=%d de %d productos escaneados",
            settings.max_products_per_run,
            len(amazon_products),
        )
        amazon_products = amazon_products[: settings.max_products_per_run]

    claude_client = None
    cj_client = None
    if not settings.test_mode:
        from matching.claude_client import ClaudeMatchingClient
        from matching.cj_client import CJClient

        claude_client = ClaudeMatchingClient()
        cj_client = CJClient()

    rows = []
    for product in amazon_products:
        match = run_matching(product, cache, claude_client, cj_client)
        if not match:
            continue
        gap = calculate_gap(
            precio_amazon=product["price"],
            precio_proveedor=match["precio_cj"],
            envio_estimado=match.get("envio_estimado", DEFAULT_ENVIO_ESTIMADO),
        )
        rows.append(
            {
                "producto_amazon": product["title"],
                "asin": product["asin"],
                "precio_amazon": product["price"],
                "reviews": product["reviews"],
                "bsr": product["bsr"],
                "producto_cj": match["producto_cj"],
                "precio_cj": match["precio_cj"],
                "url_cj": match["url_cj"],
                "envio_estimado": match.get("envio_estimado", DEFAULT_ENVIO_ESTIMADO),
                "gap_pct": gap.gap_pct,
                "margen_bruto": gap.margen_bruto,
            }
        )

    write_results(rows)
    cache.close()


if __name__ == "__main__":
    main()
