# Calidad y Evidencias

## Estrategia

El proyecto separa las pruebas por propósito para que cada reporte represente una evidencia
identificable.

| Suite | Alcance |
|---|---|
| Unitarias | Parsers, modelos, configuración, seguridad y lógica aislada |
| Contratos | Interfaz común de los 13 motores registrados |
| Integración | Motores Docker o emulados localmente |
| Interfaz | CLI, TUI, API, MCP, extensión y portal documental |
| BDD | Criterios de aceptación Dado/Cuando/Entonces |
| Mutación | Capacidad de las pruebas para detectar cambios defectuosos |

## Cobertura por motor

| Motor | Contrato | Integración |
|---|:---:|---|
| PostgreSQL | Sí | Docker |
| MySQL | Sí | Docker |
| SQLite | Sí | Archivo/memoria |
| Microsoft SQL Server | Sí | Docker en job dedicado |
| CockroachDB | Sí | Docker |
| YugabyteDB | Sí | Docker |
| MongoDB | Sí | Docker |
| Redis | Sí | Docker |
| DynamoDB | Sí | Moto/boto3 emulado |
| Cassandra | Sí | Trazas y driver simulado; servicio real cuando el driver soporte Python 3.14 |
| Elasticsearch | Sí | Docker |
| Neo4j | Sí | Docker |
| InfluxDB | Sí | Docker |

La diferencia entre contrato e integración se declara para no presentar una simulación como si
fuera evidencia de un servidor real.

## Controles automatizados

- Ruff y Ruff Format.
- mypy.
- pytest y pytest-cov.
- pytest-bdd.
- mutmut.
- Bandit.
- Semgrep.
- pip-audit.
- auditoría npm de la extensión.
- SonarCloud cuando `SONAR_TOKEN` está configurado.
- Playwright con capturas, trazas y video.

## Alcance de cobertura y umbrales

- La cobertura unitaria mide modelos, parsers, configuración, API, diagnóstico, serialización y
  contratos compartidos.
- Los adaptadores concretos de transporte, la TUI y la ejecución CLI completa se verifican en suites
  de integración e interfaz porque requieren motores, terminal o procesos externos.
- Cobertura del alcance unitario medido: mínimo 65%.
- Cero fallos en pruebas obligatorias.
- Cero secretos en reportes.
- Los findings de seguridad se publican como evidencia; su severidad determina si bloquean una
  entrega.
- El objetivo de evolución es alcanzar 70% sin excluir lógica de dominio.
