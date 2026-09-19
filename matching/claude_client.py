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
        """Valida si cj_title es REALMENTE el mismo producto que amazon_title
        (mismo mecanismo/forma de uso), no solo de la misma categoría general.

        Primera versión de este prompt era demasiado permisiva: aprobaba
        matches por categoría compartida (ej. un chopper de cuchillas fijas
        con un spiralizer de manivela, ambos "utensilios de verdura"; o un
        paño de coche con un paño de cocina, ambos "de coral fleece").
        Ahora pide razonamiento explícito antes de la respuesta final y da
        ejemplos concretos de qué SÍ y qué NO cuenta como el mismo producto.
        """
        prompt = (
            "Eres un experto en catalogacion de productos para dropshipping. "
            "Decide si dos productos son REALMENTE el mismo tipo de producto: "
            "si un cliente que compro uno se quedaria satisfecho si le mandas "
            "el otro en su lugar (misma funcion principal Y mismo mecanismo o "
            "forma de uso).\n\n"
            "NO cuentan como el mismo producto (aunque compartan categoria o "
            "palabras del titulo):\n"
            "- Mismo uso general pero mecanismo/forma distintos (ej: un "
            "chopper de cuchillas fijas NO es un spiralizer de manivela, "
            "aunque ambos sean \"utensilios para cortar verdura\").\n"
            "- Mismo material o palabras descriptivas pero uso previsto "
            "distinto (ej: un paño para coche NO es un paño de cocina, "
            "aunque ambos sean \"de microfibra\").\n"
            "- Un producto individual vs. un set/kit con piezas que el otro "
            "no tiene.\n\n"
            "SI cuentan como el mismo producto:\n"
            "- Mismo tipo de objeto, misma funcion y mecanismo, aunque "
            "cambie la marca, el color, el empaque, o el numero exacto de "
            "piezas de un set del mismo tipo (ej: un set de 24 panos de "
            "cocina y uno de 20 panos de cocina del mismo tipo SI cuentan).\n\n"
            f'Producto Amazon: "{amazon_title}"\n'
            f'Producto proveedor: "{cj_title}"\n\n'
            "Primero, en una linea de maximo 20 palabras, describe la funcion "
            "y mecanismo principal de cada producto.\n"
            "Despues, en la ULTIMA linea de tu respuesta y solo en esa linea, "
            "escribe exactamente \"ANSWER: true\" si son el mismo producto, o "
            "\"ANSWER: false\" si no lo son."
        )
        raw = self._complete(prompt, max_tokens=800)
        for line in reversed(raw.strip().splitlines()):
            line = line.strip().lower()
            if line.startswith("answer:"):
                return line.split(":", 1)[1].strip().startswith("true")
        logger.warning("validate_match: no se encontró línea 'ANSWER:' en la respuesta: %r", raw)
        return False

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
