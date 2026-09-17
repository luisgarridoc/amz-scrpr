"""Test unitario puro (sin llamadas a red) del cálculo de gap de margen."""
from calc.gap_calculator import calculate_gap


def test_calculate_gap_basic():
    result = calculate_gap(
        precio_amazon=30.0,
        precio_proveedor=8.0,
        envio_estimado=2.0,
        comision_amazon_pct=15.0,
    )
    # comision_amazon = 30 * 0.15 = 4.5
    # margen_bruto = 30 - (8 + 2 + 4.5) = 15.5
    assert result.margen_bruto == 15.5
    assert result.gap_pct == round(15.5 / 30 * 100, 2)


def test_calculate_gap_negative_margin():
    result = calculate_gap(
        precio_amazon=10.0,
        precio_proveedor=9.0,
        envio_estimado=1.0,
        comision_amazon_pct=15.0,
    )
    assert result.margen_bruto < 0
    assert result.gap_pct < 0
