"""Cliente básico para la API de Keepa (https://keepa.com/#!api).

Free tier: registra una cuenta en keepa.com, en tu perfil obtienes la
"API Key" (Settings > API). El free tier da una cuota de tokens/minuto muy
limitada, por eso este cliente usa `common.retry.with_backoff`.
"""
from __future__ import annotations

from typing import Any, Optional

import requests

from common.config import settings
from common.logging_conf import get_logger
from common.retry import raise_for_rate_limit, with_backoff

logger = get_logger(__name__)

BASE_URL = "https://api.keepa.com"

# Dominio de Amazon: 1 = amazon.com. Ver docs de Keepa para otros paises.
DEFAULT_DOMAIN = 1


class KeepaClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.keepa_api_key
        if not self.api_key:
            logger.warning("KEEPA_API_KEY no configurada: las llamadas fallarán.")

    @with_backoff()
    def get_product(self, asin: str, domain: int = DEFAULT_DOMAIN) -> dict[str, Any]:
        """Trae los datos de un único ASIN (para validar credenciales)."""
        params = {
            "key": self.api_key,
            "domain": domain,
            "asin": asin,
        }
        resp = requests.get(f"{BASE_URL}/product", params=params, timeout=15)
        raise_for_rate_limit(resp)
        data = resp.json()
        logger.info(
            "Keepa: tokens restantes=%s, productos devueltos=%s",
            data.get("tokensLeft"),
            len(data.get("products", [])),
        )
        return data

    def test_connection(self, sample_asin: str = "B0BSHF7WHW") -> bool:
        """Prueba mínima: trae 1 producto de ejemplo para verificar credenciales."""
        try:
            data = self.get_product(sample_asin)
            ok = "products" in data
            logger.info("Keepa test_connection: %s", "OK" if ok else "respuesta inesperada")
            return ok
        except Exception as exc:  # noqa: BLE001 - queremos loggear cualquier fallo de credenciales
            logger.error("Keepa test_connection falló: %s", exc)
            return False


if __name__ == "__main__":
    KeepaClient().test_connection()
