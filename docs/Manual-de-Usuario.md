# Manual de Usuario de Query Analyzer

## 1. Propósito

Query Analyzer obtiene planes, trazas y métricas observables de consultas en motores SQL,
NoSQL, grafos y series de tiempo. Este manual resume la instalación, configuración, ejecución y
exportación de evidencia.

## 2. Instalación

Desde el código fuente:

```bash
uv sync
uv run query_analyzer --help
```

También se distribuyen binarios mediante GitHub Releases, Homebrew, Scoop y Snap.

## 3. Configurar un perfil

```bash
uv run query_analyzer profile add local-postgres \
  --engine postgresql \
  --host localhost \
  --port 5432 \
  --database query_analyzer \
  --username qa
```

La contraseña se solicita de manera interactiva y se cifra antes de guardarse.

Comandos relacionados:

```bash
uv run query_analyzer profile list
uv run query_analyzer profile test local-postgres
uv run query_analyzer profile set-default local-postgres
uv run query_analyzer profile show local-postgres
```

## 4. Analizar una consulta

```bash
uv run query_analyzer analyze \
  "SELECT * FROM orders WHERE id = 1" \
  --profile local-postgres
```

Desde un archivo:

```bash
uv run query_analyzer analyze --file query.sql --profile local-postgres
```

Formatos:

```bash
uv run query_analyzer analyze "SELECT 1" --profile local-sqlite --output json
uv run query_analyzer analyze "SELECT 1" --profile local-sqlite --output markdown
```

## 5. Interfaz TUI

```bash
uv run query_analyzer
```

La TUI permite seleccionar perfiles, diagnosticar conexiones, editar consultas, revisar el
árbol del plan, consultar métricas y abrir el historial.

## 6. API REST

```bash
uv run qa-api
```

- Swagger: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyzer/explain \
  -H "Content-Type: application/json" \
  -d '{"connection":{"engine":"sqlite","database":":memory:"},"query":"SELECT 1"}'
```

## 7. Servidor MCP

```bash
uv run python -m query_analyzer.mcp_server
```

La herramienta MCP disponible es `analyze_query(query, profile)`.

## 8. Extensión de VS Code

La extensión analiza la selección activa y puede iniciar automáticamente el backend empaquetado.
También admite una API externa configurando `queryAnalyzer.apiMode`.

## 9. Interpretación del reporte

| Campo | Significado |
|---|---|
| `plan_tree` | Representación normalizada del plan |
| `raw_plan` | Evidencia original devuelta por el motor |
| `metrics` | Valores específicos disponibles |
| `execution_time_ms` | Tiempo observado por el adaptador |
| `ai_analysis` | Interpretación opcional y separada |

La ausencia de una métrica no significa valor cero. Query Analyzer no genera una puntuación
universal para comparar motores con semánticas diferentes.

## 10. Seguridad

- No compartir `config.yaml`.
- No incluir claves reales en consultas, capturas o reportes.
- Mantener la API ligada a localhost salvo que se configure autenticación.
- Revisar las consultas antes de ejecutarlas contra ambientes productivos.

## 11. Evidencias de calidad

GitHub Pages publica reportes de pruebas, cobertura, BDD, mutación, seguridad e interfaz. Los
resultados se generan sobre la misma revisión del código y se conservan como artefactos de Actions.
