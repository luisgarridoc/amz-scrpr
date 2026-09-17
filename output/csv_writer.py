"""Escritura del CSV final de oportunidades, ordenado y filtrado por gap_pct."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from common.config import settings
from common.logging_conf import get_logger

logger = get_logger(__name__)

FIELDNAMES = [
    "producto_amazon",
    "asin",
    "precio_amazon",
    "reviews",
    "bsr",
    "producto_cj",
    "precio_cj",
    "url_cj",
    "envio_estimado",
    "gap_pct",
    "margen_bruto",
]


def write_results(
    rows: list[dict[str, Any]],
    filepath: str = "output/opportunities.csv",
    min_gap_pct: float | None = None,
) -> int:
    """Filtra por min_gap_pct, ordena por gap_pct descendente y escribe el CSV.

    Devuelve el número de filas escritas.
    """
    threshold = min_gap_pct if min_gap_pct is not None else settings.min_gap_pct

    filtered = [r for r in rows if r.get("gap_pct", float("-inf")) >= threshold]
    filtered.sort(key=lambda r: r["gap_pct"], reverse=True)

    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in filtered:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})

    logger.info(
        "CSV escrito en %s: %d/%d filas pasaron el umbral min_gap_pct=%.1f",
        filepath,
        len(filtered),
        len(rows),
        threshold,
    )
    return len(filtered)
