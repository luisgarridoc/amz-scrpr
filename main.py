"""Orquestador del pipeline (v1: solo research de gaps de precio).

En TEST_MODE (default) usa scouting/sample_data.py como fuente de productos
Amazon y NO llama a Keepa/RapidAPI. El matching contra CJ y la validación
con Claude sí requieren red real -- si no tienes esas keys todavía, corre
solo test_connections.py primero.
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
    raise NotImplementedError(
        "Scouting real vía Keepa/RapidAPI aún no conectado al orquestador: "
        "valida primero las credenciales con test_connections.py."
    )


def run_matching(amazon_product: dict, cache: MatchingCache) -> dict | None:
    """Placeholder de matching: en TEST_MODE no llama a Claude/CJ todavía.

    Cuando tengas las keys, aquí se generarán variantes de búsqueda con
    ClaudeMatchingClient, se buscará en CJClient y se validará el match.
    """
    cache_key = f"asin:{amazon_product['asin']}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if settings.test_mode:
        logger.info("TEST_MODE: sin match real de CJ para %s (placeholder)", amazon_product["asin"])
        return None

    raise NotImplementedError("Matching real vía Claude + CJ pendiente de conectar aquí.")


def main() -> None:
    cache = MatchingCache()
    amazon_products = run_scouting()

    rows = []
    for product in amazon_products:
        match = run_matching(product, cache)
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
