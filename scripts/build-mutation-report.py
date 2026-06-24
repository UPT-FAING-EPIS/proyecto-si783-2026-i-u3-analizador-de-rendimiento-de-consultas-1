"""Build a small HTML report from mutmut's text results."""

from __future__ import annotations

import html
from pathlib import Path

RESULTS_FILE = Path("mutation-results.txt")
OUTPUT_FILE = Path("html/index.html")


def main() -> None:
    """Render the mutation results as a portable HTML artifact."""
    results = (
        RESULTS_FILE.read_text(encoding="utf-8") if RESULTS_FILE.exists() else "Sin resultados."
    )
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Reporte de mutación</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; color: #20242a; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #f3f5f7; padding: 1rem; }}
  </style>
</head>
<body>
  <h1>Reporte de pruebas de mutación</h1>
  <pre>{html.escape(results)}</pre>
</body>
</html>
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
