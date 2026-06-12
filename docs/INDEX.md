# Índice de documentación

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
- [Especificación de requisitos](FD03-Especificacion-Requerimientos.md)
- [Arquitectura](FD04-Informe-Arquitectura.md)
