# Query Analyzer - Documentación y Evidencias

Este índice reúne documentación académica, manuales técnicos y reportes de calidad del
**Analizador de Rendimiento de Consultas (Query Analyzer)**.

## Inicio

- [README principal](../README.md)
- [API REST](API.md)
- [Comando de análisis](cli/ANALYZE_COMMAND.md)
- [Administración de perfiles](cli/PROFILE_COMMANDS.md)

## Adaptadores

- [DynamoDB](adapters/DYNAMODB.md)
- [Cassandra](CASSANDRA_ADAPTER.md)

## Contrato actual

Query Analyzer presenta información factual obtenida del motor:

- plan de ejecución normalizado;
- plan original;
- tiempo observado;
- métricas disponibles;
- información del motor;
- interpretación opcional mediante IA, claramente separada.

El núcleo no genera puntuaciones de rendimiento ni diagnósticos deterministas de
antipatrones. Las observaciones generadas por IA no sustituyen la evidencia del
motor.

## Proyecto académico

- [Factibilidad](FD01-Informe-Factibilidad.md)
- [Visión](FD02-Informe-Vision.md)
- [Especificación de requisitos](FD03-EPIS-Informe%20Especificación%20Requerimientos.md)
- [Arquitectura](FD04-EPIS-Informe%20Arquitectura%20de%20Software.md)
- [Informe final](FD05-EPIS-Informe%20ProyectoFinal.md)
- [Estándar de programación](Estandar-de-Programacion.md)
- [Diccionario de datos](DICCIONARIO-DE-DATOS.md)
- [Manual de usuario](Manual-de-Usuario.md)
- [GitHub Project y trazabilidad](Github-Project-y-Trazabilidad.md)
- [Calidad y evidencias](Calidad-y-Evidencias.md)

## Reportes automatizados

El workflow `quality-pages.yml` publica:

- cobertura;
- pruebas unitarias;
- contratos de los 13 motores;
- integración con motores reales o emulados;
- BDD;
- mutación;
- interfaz documental;
- extensión de VS Code;
- Bandit, Semgrep y auditoría de dependencias;
- estado de SonarCloud.
