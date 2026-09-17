"""Cálculo de margen bruto y gap porcentual entre precio Amazon y proveedor CJ."""
from __future__ import annotations

from dataclasses import dataclass

from common.config import settings


@dataclass(frozen=True)
class GapResult:
    margen_bruto: float
    gap_pct: float


def calculate_gap(
    precio_amazon: float,
    precio_proveedor: float,
    envio_estimado: float,
    comision_amazon_pct: float | None = None,
) -> GapResult:
    """margen_bruto = precio_amazon - (precio_proveedor + envio_estimado + comision_amazon)
    gap_pct = margen_bruto / precio_amazon * 100
    """
    if precio_amazon <= 0:
        raise ValueError("precio_amazon debe ser > 0")

    comision_pct = (
        comision_amazon_pct if comision_amazon_pct is not None else settings.amazon_commission_pct
    )
    comision_amazon = precio_amazon * (comision_pct / 100)

    margen_bruto = precio_amazon - (precio_proveedor + envio_estimado + comision_amazon)
    gap_pct = (margen_bruto / precio_amazon) * 100

    return GapResult(margen_bruto=round(margen_bruto, 2), gap_pct=round(gap_pct, 2))
