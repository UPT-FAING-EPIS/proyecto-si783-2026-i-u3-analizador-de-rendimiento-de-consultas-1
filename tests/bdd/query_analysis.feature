# language: es
Característica: Analizar consultas con evidencia factual
  Como estudiante o desarrollador de bases de datos
  Quiero obtener reportes consistentes para todos los motores soportados
  Para comparar planes y métricas sin confundir hechos con interpretaciones

  Esquema del escenario: Reconocer los motores soportados
    Dado que Query Analyzer está inicializado
    Cuando consulto si el motor "<motor>" está registrado
    Entonces el motor aparece como soportado

    Ejemplos:
      | motor         |
      | postgresql    |
      | mysql         |
      | sqlite        |
      | mssql         |
      | cockroachdb   |
      | yugabytedb    |
      | mongodb       |
      | redis         |
      | dynamodb      |
      | cassandra     |
      | elasticsearch |
      | neo4j         |
      | influxdb      |

  Escenario: Mantener separados los datos factuales y la IA
    Dado un reporte factual de SQLite
    Cuando serializo el reporte a JSON
    Entonces el reporte no contiene una puntuación universal
    Y el análisis de IA permanece ausente

  Escenario: Proteger los secretos durante un diagnóstico
    Dado una conexión PostgreSQL con una contraseña sensible
    Cuando sanitizo un error que contiene la contraseña
    Entonces el mensaje no revela el secreto
