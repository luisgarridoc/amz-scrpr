"""Cliente básico para la API de Claude (Anthropic), usado en la etapa de
MATCHING para:
  1) generar 2-3 variantes de búsqueda a partir de un título de Amazon.
  2) validar semánticamente si un resultado de CJ es el mismo producto.

Registro: crea cuenta en https://console.anthropic.com/, genera una API key
en "API Keys" y ponla en ANTHROPIC_API_KEY. El modelo se configura vía
ANTHROPIC_MODEL (por defecto "claude-sonnet-5" en este proyecto: el ID
"claude-sonnet-4-6" mencionado en la idea original no corresponde a un
modelo vigente; ajusta ANTHROPIC_MODEL si tu cuenta expone otro ID).
"""
from __future__ import annotations

import json
from typing import Optional

import anthropic

from common.config import settings
from common.logging_conf import get_logger
from common.retry import with_backoff

logger = get_logger(__name__)


def _strip_code_fence(raw: str) -> str:
    """Quita el envoltorio ```json ... ``` / ``` ... ``` que Claude a veces
    añade aunque se le pida "solo JSON"."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[: -3]
        text = text.strip()
    return text


def _extract_json_array(raw: str) -> str:
    """Aísla el primer "[...]" del texto -- cubre casos como Claude
    devolviendo literalmente 'json["a", "b"]' sin backticks de code fence."""
    text = _strip_code_fence(raw)
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


class ClaudeMatchingClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.anthropic_model
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY no configurada: las llamadas fallarán.")
        self._client = anthropic.Anthropic(api_key=self.api_key) if self.api_key else None

    @with_backoff()
    def _complete(self, prompt: str, max_tokens: int = 300) -> str:
        assert self._client is not None, "Cliente Anthropic no inicializado (falta API key)"
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        # resp.content puede traer bloques de "thinking" antes del texto
        # (algunos modelos/cuentas los devuelven aunque no se pida extended
        # thinking); nos quedamos con el primer bloque que sea texto real.
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                return block.text
        raise RuntimeError(f"Respuesta de Claude sin bloque de texto: {resp.content!r}")

    def generate_search_variants(self, amazon_title: str, n: int = 3) -> list[str]:
        """Genera n variantes de búsqueda cortas para buscar en CJdropshipping."""
        prompt = (
            "Eres un asistente de sourcing de dropshipping. Dado el titulo de un "
            f"producto de Amazon, genera {n} variantes de busqueda cortas (2-5 "
            "palabras, en ingles, sin marca) que podrian usarse para encontrar el "
            "mismo producto generico en un catalogo de proveedores mayoristas.\n\n"
            f"Titulo Amazon: {amazon_title}\n\n"
            'Responde SOLO con un JSON array de strings, ej: ["variant 1", "variant 2"]'
        )
        raw = _extract_json_array(self._complete(prompt))
        try:
            variants = json.loads(raw)
            if isinstance(variants, list):
                return [str(v) for v in variants][:n]
        except json.JSONDecodeError:
            logger.warning("No se pudo parsear JSON de variantes, devolviendo texto crudo: %s", raw)
        return [raw]

    def validate_match(self, amazon_title: str, cj_title: str) -> bool:
        """Valida semánticamente si cj_title es el mismo producto (o muy similar)."""
        prompt = (
            "Responde SOLO 'true' o 'false' (sin explicacion): dado que un producto "
            f"de Amazon se llama \"{amazon_title}\" y un producto de un proveedor se "
            f"llama \"{cj_title}\", son el mismo producto generico o muy similar "
            "(mismo tipo de item, funcion y forma), ignorando diferencias de marca, "
            "color o empaque?"
        )
        raw = self._complete(prompt, max_tokens=200).strip().lower()
        return raw.startswith("true")

    def test_connection(self) -> bool:
        """Prueba mínima: genera variantes para un título de ejemplo."""
        try:
            variants = self.generate_search_variants("Mini portable neck massager USB rechargeable")
            ok = len(variants) > 0
            logger.info("Claude test_connection: %s -> %s", "OK" if ok else "vacío", variants)
            return ok
        except Exception as exc:  # noqa: BLE001
            logger.error("Claude test_connection falló: %s", exc)
            return False


if __name__ == "__main__":
    ClaudeMatchingClient().test_connection()
