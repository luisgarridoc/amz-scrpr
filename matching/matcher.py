"""Orquesta la etapa de MATCHING: genera variantes de búsqueda con Claude,
busca candidatos en el catálogo de CJdropshipping y valida semánticamente
cuál es (si hay alguno) el mismo producto que el de Amazon.
"""
from __future__ import annotations

from typing import Optional

from common.logging_conf import get_logger
from matching.cj_client import CJClient, parse_product_list
from matching.claude_client import ClaudeMatchingClient

logger = get_logger(__name__)

# Cuántos candidatos de CJ (deduplicados entre variantes) se validan como
# máximo con Claude por producto de Amazon -- limita el gasto de API.
MAX_CANDIDATES_TO_VALIDATE = 5

DEFAULT_ENVIO_ESTIMADO = 3.0
ENVIO_ESTIMADO_FREE_SHIPPING = 0.0


def find_best_match(
    amazon_title: str,
    claude: ClaudeMatchingClient,
    cj: CJClient,
) -> Optional[dict]:
    """Busca el mejor equivalente de `amazon_title` en el catálogo de CJ.

    Devuelve None si ningún candidato fue validado como el mismo producto,
    o un dict {producto_cj, precio_cj, url_cj, envio_estimado} del match más
    barato entre los que Claude validó como equivalentes (a menor precio de
    proveedor, mayor margen potencial).
    """
    variants = claude.generate_search_variants(amazon_title)
    logger.info("Variantes de búsqueda para %r: %s", amazon_title, variants)

    candidates: dict[str, dict] = {}
    for variant in variants:
        try:
            raw = cj.search_products(variant, page_size=5)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Búsqueda en CJ falló para variante %r: %s", variant, exc)
            continue
        for item in parse_product_list(raw):
            candidates.setdefault(item["pid"], item)
        if len(candidates) >= MAX_CANDIDATES_TO_VALIDATE:
            break

    if not candidates:
        logger.info("Sin candidatos en CJ para %r", amazon_title)
        return None

    validated = []
    for item in list(candidates.values())[:MAX_CANDIDATES_TO_VALIDATE]:
        try:
            is_match = claude.validate_match(amazon_title, item["title"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Validación de match falló para %r: %s", item["title"], exc)
            continue
        if is_match:
            validated.append(item)

    if not validated:
        logger.info("Ningún candidato de CJ validado semánticamente para %r", amazon_title)
        return None

    best = min(validated, key=lambda i: i["price"])
    envio_estimado = (
        ENVIO_ESTIMADO_FREE_SHIPPING if best.get("is_free_shipping") else DEFAULT_ENVIO_ESTIMADO
    )

    logger.info("Match elegido para %r: %r (precio=%.2f)", amazon_title, best["title"], best["price"])
    return {
        "producto_cj": best["title"],
        "precio_cj": best["price"],
        "url_cj": best["url"],
        "envio_estimado": envio_estimado,
    }
