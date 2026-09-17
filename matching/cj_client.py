"""Cliente básico para la API oficial de CJdropshipping.

Registro: crea cuenta en https://cjdropshipping.com/, luego solicita acceso
de API en https://developers.cjdropshipping.com/ (te dan un "API Key" /
"Access Token" ligado a tu email). CJ usa un flujo de autenticación por
token: se hace login contra /authentication/getAccessToken con email +
password/API key, y el accessToken devuelto se manda en el header
"CJ-Access-Token" en las siguientes llamadas. Aquí lo modelamos con
CJ_API_KEY (email o api key) y CJ_API_SECRET (password o secret), según
el modo de auth que tengas habilitado en tu cuenta.
"""
from __future__ import annotations

from typing import Any, Optional

import requests

from common.config import settings
from common.logging_conf import get_logger
from common.retry import raise_for_rate_limit, with_backoff

logger = get_logger(__name__)

BASE_URL = "https://developers.cjdropshipping.com/api2.0/v1"


class CJClient:
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key or settings.cj_api_key
        self.api_secret = api_secret or settings.cj_api_secret
        self._access_token: Optional[str] = None
        if not self.api_key or not self.api_secret:
            logger.warning("CJ_API_KEY / CJ_API_SECRET no configurados: las llamadas fallarán.")

    @with_backoff()
    def get_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        url = f"{BASE_URL}/authentication/getAccessToken"
        payload = {"email": self.api_key, "password": self.api_secret}
        resp = requests.post(url, json=payload, timeout=15)
        raise_for_rate_limit(resp)
        data = resp.json()
        token = data.get("data", {}).get("accessToken")
        if not token:
            raise RuntimeError(f"CJ no devolvió accessToken: {data}")
        self._access_token = token
        logger.info("CJ: access token obtenido correctamente.")
        return token

    @with_backoff()
    def search_products(self, keyword: str, page_size: int = 10) -> dict[str, Any]:
        """Busca productos por keyword en el catálogo de CJ."""
        token = self.get_access_token()
        url = f"{BASE_URL}/product/list"
        headers = {"CJ-Access-Token": token}
        params = {"productName": keyword, "pageSize": page_size}
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        raise_for_rate_limit(resp)
        return resp.json()

    def test_connection(self, sample_keyword: str = "phone case") -> bool:
        """Prueba mínima: autenticación + 1 búsqueda de ejemplo."""
        try:
            data = self.search_products(sample_keyword, page_size=1)
            ok = bool(data)
            logger.info("CJ test_connection: %s", "OK" if ok else "respuesta vacía")
            return ok
        except Exception as exc:  # noqa: BLE001
            logger.error("CJ test_connection falló: %s", exc)
            return False


if __name__ == "__main__":
    CJClient().test_connection()
