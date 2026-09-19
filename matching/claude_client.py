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
        """Valida si cj_title es CASI IDÉNTICO a amazon_title -- no solo de
        la misma categoría ni con función parecida, sino el tipo de producto
        que un cliente aceptaría sin notar el cambio si le mandas el otro.

        v1 del prompt solo pedia "mismo tipo de item, funcion y forma" sin
        ejemplos, y aprobaba por categoria compartida (chopper vs spiralizer,
        ambos "utensilio de verdura"; paño de coche vs paño de cocina, ambos
        "de coral fleece"). v2 anadio ejemplos de mecanismo distinto pero
        seguia siendo permisiva con especificaciones (tamaño/capacidad/
        material/funciones) distintas dentro del mismo mecanismo. v3 exige
        comparar explicitamente esas especificaciones, no solo el mecanismo.
        """
        prompt = (
            "Eres un experto en control de calidad de catalogacion para "
            "dropshipping. Decide si el Producto B es CASI IDENTICO al "
            "Producto A -- no \"de la misma categoria\" ni \"con funcion "
            "parecida\", sino el tipo de producto que un cliente aceptaria "
            "sin notar el cambio si le mandas B en vez de A.\n\n"
            "Compara explicitamente estos aspectos:\n"
            "1. Mecanismo / forma de uso exacta (como funciona).\n"
            "2. Especificaciones clave: tamaño, capacidad, material, "
            "potencia, numero de piezas o funciones incluidas.\n\n"
            "RECHAZA (false) si:\n"
            "- El mecanismo es distinto, aunque la categoria general sea la "
            "misma (ej: un chopper de cuchillas fijas NO es un spiralizer "
            "de manivela, aunque ambos sean \"utensilio para verdura\").\n"
            "- El uso previsto es distinto aunque compartan material o "
            "palabras del titulo (ej: un paño de coche NO es un paño de "
            "cocina, aunque ambos sean \"de microfibra\").\n"
            "- Las especificaciones clave difieren de forma notable (ej: "
            "24oz vs 12oz de capacidad, un set de 5 piezas vs uno de 14 con "
            "funciones distintas, potencia/material que cambia el uso).\n"
            "- Uno tiene funciones o accesorios relevantes que el otro no "
            "tiene.\n\n"
            "ACEPTA (true) SOLO si:\n"
            "- Mismo mecanismo Y especificaciones clave equivalentes (se "
            "permite tolerancia razonable: 24oz vs 25oz si cuenta, 24oz vs "
            "12oz no; un set de 24 piezas vs uno de 20 del mismo tipo si "
            "cuenta, un set de 5 piezas vs uno de 14 con piezas distintas "
            "no).\n"
            "- Las unicas diferencias son marca, color o empaque.\n\n"
            f'Producto A (Amazon): "{amazon_title}"\n'
            f'Producto B (proveedor): "{cj_title}"\n\n'
            "Primero, en maximo 2 lineas, compara mecanismo y especificaciones "
            "clave de A vs B.\n"
            "Despues, en la ULTIMA linea de tu respuesta y solo en esa linea, "
            "escribe exactamente \"ANSWER: true\" si son casi identicos, o "
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
