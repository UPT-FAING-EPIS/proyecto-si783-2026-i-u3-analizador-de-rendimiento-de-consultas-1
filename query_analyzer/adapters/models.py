"""Modelos de datos para adapters de bases de datos."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator


class ConnectionConfig(BaseModel):
    """Configuración de conexión a una base de datos.

    Attributes:
        engine: Motor de base de datos (postgresql, mysql, sqlite, mongodb, etc.)
        host: Dirección del servidor (optional for SQLite)
        port: Puerto de conexión (optional for SQLite)
        database: Nombre o ruta de la base de datos
        username: Usuario para autenticación (optional for SQLite)
        password: Contraseña para autenticación. Puede ser vacío para:
                 - CockroachDB (root sin contraseña en docker)
                 - SQLite (file-based, no auth)
                 Otros engines requieren password no-vacío si se proporciona.
        extra: Parámetros adicionales específicos del motor
    """

    engine: str
    host: str | None = None
    port: int | None = None
    database: str
    username: str | None = None
    password: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("engine", mode="before")
    @classmethod
    def validate_engine(cls, v: str) -> str:
        """Validate and normalize engine name to lowercase.

        Args:
            v: Engine name

        Returns:
            Lowercase engine name

        Raises:
            ValueError: If engine is not supported
        """
        if not v or not v.strip():
            raise ValueError("engine no puede estar vacío")

        engine_lower = v.strip().lower()
        valid_engines = {
            "postgresql",
            "mysql",
            "sqlite",
            "mongodb",
            "redis",
            "neo4j",
            "cockroachdb",
            "yugabytedb",
            "influxdb",
            "dynamodb",
            "cassandra",
            "elasticsearch",
            "mssql",
        }

        if engine_lower not in valid_engines:
            raise ValueError("Motor no soportado")

        return engine_lower

    @field_validator("host", mode="before")
    @classmethod
    def strip_host(cls, v: str | None) -> str | None:
        """Strip whitespace from host."""
        if v is None:
            return None

        stripped = v.strip()
        if not stripped:
            raise ValueError("host no puede estar vacío")

        return stripped

    @field_validator("database", mode="before")
    @classmethod
    def strip_and_validate_database(cls, v: str, info: ValidationInfo) -> str:
        """Strip whitespace and validate database name.

        Args:
            v: Database name
            info: Validation context with engine information

        Returns:
            Stripped database name (may be empty for some engines)

        Raises:
            ValueError: If database is empty for engines that require it
        """
        if not v:
            v = ""

        stripped = v.strip() if isinstance(v, str) else ""

        # Engines that don't require a database name
        engine = info.data.get("engine", "").lower()
        no_database_required = {
            "elasticsearch",
            "dynamodb",
            "redis",
            "cassandra",
        }

        # Allow empty database for engines that don't use the concept
        if engine in no_database_required:
            return stripped

        # Other engines require non-empty database
        if not stripped:
            raise ValueError("database no puede estar vacío")

        return stripped

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, v: str | None) -> str | None:
        """Strip whitespace from username."""
        if v is None:
            return None

        stripped = v.strip()
        if stripped == "":
            raise ValueError("username no puede estar vacío")

        return stripped

    @field_validator("password", mode="before")
    @classmethod
    def strip_password(cls, v: str | None) -> str | None:
        """Strip whitespace from password.

        Note: Password validation is now delegated to model_validator
        to handle engine-specific rules (e.g., CockroachDB allows empty).
        """
        if v is None:
            return None

        stripped = v.strip()
        return stripped if stripped else ""

    @model_validator(mode="after")
    def validate_password_by_engine(self) -> ConnectionConfig:
        """Validate password based on engine type.

        CockroachDB allows empty password (uses root without auth in docker).
        Other engines require non-empty password.

        Raises:
            ValueError: If password is empty for engines that require it
        """
        engine = (self.engine or "").lower()

        # CockroachDB allows empty password (typical in docker/local dev)
        if engine in {"cockroachdb", "cockroach"}:
            return self

        # SQLite also allows empty/None password (file-based, no auth)
        if engine == "sqlite":
            return self

        # For other engines, enforce non-empty password if username is provided
        # (password might be None for no-auth scenarios, but if provided, can't be empty)
        if self.password is not None and self.password == "":
            raise ValueError("password no puede estar vacío")

        return self

    @field_validator("port", mode="before")
    @classmethod
    def validate_port(cls, v: int | None, info: ValidationInfo) -> int | None:
        """Validate port number and set defaults based on engine.

        Args:
            v: Port number if provided
            info: Validation context with engine information

        Returns:
            Default port for engine or provided value

        Raises:
            ValueError: If port is out of valid range (1-65535)
        """
        if v is not None:
            if v <= 0 or v > 65535:
                raise ValueError("Puerto debe estar entre 1 y 65535")
            return v

        engine = info.data.get("engine", "").lower()
        if engine == "mongodb":
            return 27017
        elif engine == "postgresql":
            return 5432
        elif engine == "mysql":
            return 3306
        elif engine == "mssql":
            return 1433
        elif engine == "redis":
            return 6379
        elif engine == "neo4j":
            return 7687
        elif engine == "elasticsearch":
            return 9200
        elif engine == "sqlite":
            return None
        elif engine == "dynamodb":
            return None
        return v

    def model_post_init(self, __context: Any) -> None:
        """Configure database-specific settings after initialization.

        Automatically sets authSource to 'admin' for MongoDB if username is provided.

        Args:
            __context: Pydantic context (unused)
        """
        if self.engine.lower() == "mongodb":
            if self.username and not self.extra.get("authSource"):
                self.extra["authSource"] = "admin"


class PlanNode(BaseModel):
    """Nodo del árbol de ejecución - agnóstico al motor.

    Estructura jerárquica que representa planes de cualquier BD:
    - SQL: Seq Scan → Index Scan → Join → Sort
    - NoSQL: COLLSCAN → IXSCAN → Group → Output
    - Neo4j: ProduceResults → Apply → NodeIndexSeek
    - InfluxDB: range → filter → group → aggregation

    Ejemplos de properties por motor:
    - PostgreSQL: table_name, index_name, filter_condition, buffers
    - MongoDB: stage, collection, input_docs, output_docs
    - Neo4j: operator, operands, rows_created
    - InfluxDB: bucket_name, time_range, function
    """

    node_type: str
    """Tipo de operación (Seq Scan, Index Scan, Join, etc.)"""

    cost: float | None = None
    """Costo estimado por el optimizador"""

    estimated_rows: int | None = None
    """Filas que el optimizador predice"""

    actual_rows: int | None = None
    """Filas reales retornadas/procesadas"""

    actual_time_ms: float | None = None
    """Tiempo real de ejecución en ms"""

    children: list[PlanNode] = Field(default_factory=list)
    """Nodos hijo (recursivo)"""

    properties: dict[str, Any] = Field(default_factory=dict)
    """Propiedades específicas: table_name, filter_condition, etc."""

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("node_type")
    @classmethod
    def validate_node_type(cls, v: str) -> str:
        """Valida que node_type no esté vacío."""
        if not v or not v.strip():
            raise ValueError("node_type no puede estar vacío")
        return v.strip()


class AIAnalysisResult(BaseModel):
    """Resultado del análisis con IA - v2.1.0.

    Contiene insights en lenguaje natural sobre el plan de ejecución.
    Solo poblado si el usuario configura QA_AI_BASE_URL y QA_AI_API_KEY.

    Attributes:
        summary: Resumen del EXPLAIN en lenguaje natural
        observations: Observaciones puntuales del plan
        recommendations: Recomendaciones accionables
        raw_response: Respuesta completa de la IA (para debugging)
    """

    summary: str
    """Resumen del EXPLAIN en lenguaje natural"""

    observations: list[str] = Field(default_factory=list)
    """Observaciones puntuales del plan"""

    recommendations: list[str] = Field(default_factory=list)
    """Recomendaciones accionables"""

    raw_response: str | None = None
    """Respuesta completa de la IA (para debugging)"""

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: str) -> str:
        """Valida que summary no esté vacío."""
        if not v or not v.strip():
            raise ValueError("summary no puede estar vacío")
        return v.strip()


class QueryAnalysisReport(BaseModel):
    """Reporte de análisis de consulta - Modelo v2.1.0.

    Enfoque en datos reales del EXPLAIN o equivalente del motor.
    La interpretación en lenguaje natural vive únicamente en ``ai_analysis``
    y nunca se mezcla con las métricas observadas.

    Attributes:
        engine: Motor de base de datos que ejecutó el análisis
        query: Consulta SQL analizada
        execution_time_ms: Tiempo de ejecución en milisegundos
        plan_tree: Árbol jerárquico del plan de ejecución
        plan_summary: Resumen simple del plan
        ai_analysis: Análisis con IA (si QA_AI_* configuradas)
        analyzed_at: Timestamp UTC de cuándo se realizó el análisis
        raw_plan: Plan de ejecución completo del motor (compatibilidad)
        metrics: Métricas adicionales del plan
    """

    engine: str
    """Motor BD: postgresql, mysql, mongodb, neo4j, influxdb, etc."""

    query: str
    """Consulta original analizada"""

    execution_time_ms: float
    """Tiempo de ejecución en milisegundos"""

    plan_tree: PlanNode | None = None
    """Árbol jerárquico del plan de ejecución

    Construido desde el plan normalizado del parser.
    None si el motor no proporciona plan (ej: Redis).
    """

    plan_summary: str = ""
    """Resumen simple del plan (ej: 'Index Scan on users').

    Generado por el adapter sin IA, siempre disponible.
    """

    ai_analysis: AIAnalysisResult | None = None
    """Análisis con IA (si QA_AI_BASE_URL configurada).

    None si:
    - Usuario no configuró variables de entorno de IA
    - Error al contactar el proveedor de IA
    - Usuario ejecutó sin IA deliberadamente
    """

    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """Timestamp UTC de cuándo se realizó el análisis

    ✅ IMPORTANTE: Siempre UTC para consistencia global
    Serialización JSON: ISO 8601 format
    """

    raw_plan: dict[str, Any] | None = None
    """Plan original del motor (JSON/dict) - compatibilidad

    Preservado para:
    - Debugging
    - Comparativas futuras
    - Código legacy que lo requiera
    """

    metrics: dict[str, Any] = Field(default_factory=dict)
    """Métricas adicionales específicas del parser

    Ejemplos:
    - PostgreSQL: node_count, buffers_hit, buffers_read
    - MongoDB: examination_ratio, index_scans
    - InfluxDB: bucket_size, transformation_count
    """

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("engine", mode="before")
    @classmethod
    def validate_report_engine(cls, v: str) -> str:
        """Validate and normalize engine name to lowercase.

        Args:
            v: Engine name

        Returns:
            Lowercase engine name

        Raises:
            ValueError: If engine is not supported
        """
        if not v or not v.strip():
            raise ValueError("engine no puede estar vacío")

        engine_lower = v.strip().lower()
        valid_engines = {
            "postgresql",
            "mysql",
            "sqlite",
            "mongodb",
            "redis",
            "neo4j",
            "cockroachdb",
            "yugabytedb",
            "influxdb",
            "dynamodb",
            "cassandra",
            "elasticsearch",
            "mssql",
        }

        if engine_lower not in valid_engines:
            raise ValueError("Motor no soportado")

        return engine_lower

    @field_validator("execution_time_ms")
    @classmethod
    def validate_execution_time(cls, v: float) -> float:
        """Valida que execution_time_ms sea positivo (> 0).

        Note: 0 is rejected as it indicates a query that took unmeasurable time.
        """
        if v <= 0:
            raise ValueError("execution_time_ms debe ser mayor a 0")
        return v
