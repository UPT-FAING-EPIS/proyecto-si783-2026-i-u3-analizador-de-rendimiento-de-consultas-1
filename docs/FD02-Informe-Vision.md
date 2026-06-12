# FD02 - Informe de visión

## Visión

Query Analyzer será una herramienta local y extensible para inspeccionar planes,
métricas y características observables de consultas en múltiples motores desde
CLI, TUI o API REST.

## Usuarios

- Estudiantes de bases de datos.
- Desarrolladores.
- Administradores de bases de datos.
- Equipos que necesitan recopilar evidencia antes y después de una optimización.

## Capacidades

1. Administración segura de perfiles.
2. Diagnóstico de conectividad con estados verificables.
3. Registro de adaptadores por motor.
4. Ejecución de `EXPLAIN` o mecanismo equivalente.
5. Normalización de árboles y métricas.
6. Presentación CLI y TUI.
7. Exportación estructurada.
8. API REST local.
9. Interpretación opcional mediante proveedores de IA compatibles.

## Principios

- Datos del motor antes que heurísticas.
- Diferenciar ausencia de datos de valor cero.
- No comparar métricas incompatibles.
- No generar score de calidad.
- Mantener IA separada de la evidencia.
- No exponer contraseñas, tokens ni claves.

## Alcance actual

El sistema soporta adaptadores para PostgreSQL, MySQL, SQLite, SQL Server,
CockroachDB, YugabyteDB, MongoDB, Redis, Elasticsearch, DynamoDB, Cassandra,
Neo4j e InfluxDB, con distinta profundidad según las capacidades de cada motor.

## Fuera de alcance

- Aplicar cambios de esquema automáticamente.
- Garantizar que una sugerencia de IA mejore el rendimiento.
- Reemplazar monitoreo continuo de producción.
- Producir una puntuación universal 0-100.

## Resultado esperado

El usuario obtiene un reporte reproducible que sirve para estudiar el plan,
contrastar ejecuciones y justificar decisiones con evidencia.
