"""Tests for AI analysis parsing."""

from query_analyzer.core.ai_analyzer import AIAnalyzer


def test_parse_spanish_ai_response_with_suggested_query() -> None:
    """Parsea una respuesta de IA en español con consulta sugerida."""
    response = """RESUMEN:
La consulta hace un escaneo completo de usuarios, por lo que puedes mejorarla filtrando por una columna indexada.

OBSERVACIONES:
- ALTO: Se detecta un escaneo secuencial sobre users.
- MEDIO: El filtro reduce filas despues de leer la tabla.

RECOMENDACIONES:
- Agrega un indice sobre users.email si esta consulta es frecuente.
- Evita seleccionar columnas que no necesitas.

CONSULTA_SUGERIDA:
SELECT id, email FROM users WHERE email = 'ana@example.com';"""

    result = AIAnalyzer()._parse_response(response)

    assert result.summary.startswith("La consulta hace un escaneo completo")
    assert result.observations == [
        "ALTO: Se detecta un escaneo secuencial sobre users.",
        "MEDIO: El filtro reduce filas despues de leer la tabla.",
    ]
    assert result.recommendations == [
        "Agrega un indice sobre users.email si esta consulta es frecuente.",
        "Evita seleccionar columnas que no necesitas.",
    ]
    assert result.suggested_query == "SELECT id, email FROM users WHERE email = 'ana@example.com';"


def test_parse_spanish_ai_response_without_suggested_query() -> None:
    """Ignora la consulta sugerida cuando la IA indica que no aplica."""
    response = """RESUMEN:
La consulta ya usa un indice adecuado.

CONSULTA_SUGERIDA:
No aplica."""

    result = AIAnalyzer()._parse_response(response)

    assert result.summary == "La consulta ya usa un indice adecuado."
    assert result.suggested_query is None


def test_parse_compact_spanish_ai_response_without_blank_lines() -> None:
    """Parsea secciones aunque no estén separadas por líneas en blanco."""
    response = """RESUMEN:
Usas un Seq Scan sobre customers.
OBSERVACIONES:
1. ALTO: La columna email no parece usar indice.
2. MEDIO: El motor descarta muchas filas.
RECOMENDACIONES:
* Crea un indice sobre customers(email).
* Selecciona columnas concretas si no necesitas todas.
CONSULTA SUGERIDA:
SELECT id, email FROM customers WHERE email = 'customer50@example.com';"""

    result = AIAnalyzer()._parse_response(response)

    assert result.summary == "Usas un Seq Scan sobre customers."
    assert result.observations == [
        "ALTO: La columna email no parece usar indice.",
        "MEDIO: El motor descarta muchas filas.",
    ]
    assert result.recommendations == [
        "Crea un indice sobre customers(email).",
        "Selecciona columnas concretas si no necesitas todas.",
    ]
    assert (
        result.suggested_query
        == "SELECT id, email FROM customers WHERE email = 'customer50@example.com';"
    )
