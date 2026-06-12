"""MongoDB adapter for query performance analysis."""

import json
import time
from datetime import UTC, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.errors import (
    ConnectionFailure,
    OperationFailure,
    ServerSelectionTimeoutError,
)

from ..base import BaseAdapter
from ..exceptions import ConnectionError as AdapterConnectionError
from ..exceptions import QueryAnalysisError
from ..models import ConnectionConfig, QueryAnalysisReport
from ..registry import AdapterRegistry
from .mongodb_parser import MongoExplainParser


@AdapterRegistry.register("mongodb")
class MongoDBAdapter(BaseAdapter):
    """Adapter for MongoDB query performance analysis.

    Supports: .find() queries with executionStats analysis.
    Not supported (Phase 2): Aggregation pipelines.
    """

    def __init__(self, config: ConnectionConfig) -> None:
        """Initialize MongoDB adapter."""
        super().__init__(config)
        self._client: MongoClient | None = None
        self._db: Any = None

    def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            # Build connection parameters
            host = self._config.host or "localhost"
            port = self._config.port or 27017
            database = self._config.database
            username = self._config.username
            password = self._config.password
            auth_source = self._config.extra.get("authSource", "admin")

            # Build URI
            if username and password:
                uri = (
                    f"mongodb://{username}:{password}@{host}:{port}/"
                    f"{database}?authSource={auth_source}"
                )
            else:
                uri = f"mongodb://{host}:{port}/{database}"

            # Connect with timeout
            self._client = MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000,
            )

            # Verify connection
            self._client.admin.command("ping")

            # Get database
            self._db = self._client[database]
            self._is_connected = True

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            raise AdapterConnectionError(
                f"Failed to connect to MongoDB at {host}:{port}: {e}"
            ) from e
        except Exception as e:
            raise AdapterConnectionError(f"Unexpected error connecting to MongoDB: {e}") from e

    def disconnect(self) -> None:
        """Close MongoDB connection."""
        try:
            if self._client:
                self._client.close()
            self._is_connected = False
        except Exception as e:
            # Log but don't raise - cleanup should not fail
            print(f"Warning: Error disconnecting from MongoDB: {e}")

    def test_connection(self) -> bool:
        """Test connection with ping command.

        Returns:
            True if connection is valid, False otherwise.
        """
        try:
            if self._client is None:
                return False
            self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def execute_explain(self, query: str) -> QueryAnalysisReport:
        """Execute EXPLAIN on MongoDB query.

        Args:
            query: JSON string with structure:
                {
                    "collection": "users",
                    "filter": {"age": {"$gt": 18}},
                    "sort": {"name": 1},
                    "projection": {"name": 1, "email": 1}
                }

        Returns:
            QueryAnalysisReport con EXPLAIN real del motor

        Raises:
            QueryAnalysisError: If query execution fails

        Note:
            v2.1.0: Retorna EXPLAIN real sin asignar una valoración global.
            IA analysis se agrega en CLI si QA_AI_BASE_URL configurada.
        """
        try:
            if not self._is_connected or self._db is None:
                raise QueryAnalysisError("Not connected to MongoDB")

            # Parse input JSON
            query_dict = json.loads(query)
            collection_name = query_dict.get("collection")
            filter_dict = query_dict.get("filter", {})
            sort_dict = query_dict.get("sort")
            projection_dict = query_dict.get("projection")

            if not collection_name:
                raise QueryAnalysisError("Query must specify 'collection' field")

            # Get collection
            collection = self._db[collection_name]

            # Execute EXPLAIN with execution statistics using find()
            # pymongo's find().explain() returns executionStats with full stage info
            kwargs = {}
            if projection_dict:
                kwargs["projection"] = projection_dict

            cursor = collection.find(filter_dict, **kwargs)
            if sort_dict:
                cursor = cursor.sort(list(sort_dict.items()))
            cursor = cursor.limit(1)

            explain_result = cursor.explain()

            # Parse explain output
            parsed_explain = MongoExplainParser.parse(explain_result)

            # Build PlanNode tree from MongoDB stages
            plan_tree = MongoExplainParser.build_plan_tree(explain_result)

            # Extract metrics
            docs_returned = parsed_explain["metrics"]["documents_returned"]
            docs_examined = parsed_explain["metrics"]["documents_examined"]
            examination_ratio = docs_examined / max(1, docs_returned)
            execution_time_ms = parsed_explain["metrics"]["execution_time_ms"]

            # Ensure execution_time_ms > 0 (validation requirement)
            if execution_time_ms <= 0:
                execution_time_ms = 1.0

            # Generate simple plan summary
            plan_summary = self._summarize_plan(explain_result)

            # Build report with v2 models (no score, no anti-patterns)
            report = QueryAnalysisReport(
                engine="mongodb",
                query=query,
                execution_time_ms=execution_time_ms,
                plan_tree=plan_tree,
                plan_summary=plan_summary,
                ai_analysis=None,  # ← Se agrega en CLI si hay IA configurada
                analyzed_at=datetime.now(UTC),
                raw_plan=explain_result,
                metrics={
                    "documents_returned": docs_returned,
                    "documents_examined": docs_examined,
                    "keys_examined": parsed_explain["metrics"]["keys_examined"],
                    "execution_stages": parsed_explain["metrics"]["execution_stages"],
                    "examination_ratio": examination_ratio,
                },
            )

            return report

        except json.JSONDecodeError as e:
            raise QueryAnalysisError(f"Invalid query JSON: {e}") from e
        except OperationFailure as e:
            raise QueryAnalysisError(f"MongoDB query failed: {e}") from e
        except Exception as e:
            raise QueryAnalysisError(f"Failed to analyze query: {e}") from e

    def _summarize_plan(self, explain_result: dict[str, Any]) -> str:
        """Genera un resumen simple del plan de ejecución MongoDB.

        Args:
            explain_result: Result from cursor.explain()

        Returns:
            Cadena con resumen simple (ej: "COLLSCAN" o "IXSCAN")
        """
        execution_stages = explain_result.get("executionStages", {})
        stage = execution_stages.get("stage", "Unknown")

        # Add key information if available
        if "executionStages" in execution_stages:
            substages = execution_stages.get("executionStages", [])
            if substages:
                if isinstance(substages, list) and len(substages) > 0:
                    first_substage = substages[0].get("stage", "")
                    if first_substage:
                        return f"{stage} → {first_substage}"

        return str(stage)

    def get_slow_queries(self, threshold_ms: int = 100) -> list[dict]:
        """Retrieve slow queries from profiling.

        Temporarily enables profiling, captures queries, restores original level.

        Args:
            threshold_ms: Queries slower than this (milliseconds)

        Returns:
            List of slow query metadata

        Raises:
            QueryAnalysisError: If profiling operations fail
        """
        try:
            if not self._is_connected or self._db is None:
                raise QueryAnalysisError("Not connected to MongoDB")

            # 1. Read current profiling level
            try:
                profile_status = self._db.command("profile", -1)
                original_level = profile_status.get("was", 0)
            except OperationFailure:
                original_level = 0

            try:
                # 2. Enable profiling level 1 (log all operations)
                self._db.command("profile", 1)

                # 3. Wait for profiling to activate
                time.sleep(0.5)

                # 4. Query system.profile collection
                profile_docs = list(
                    self._db.system.profile.find({"millis": {"$gte": threshold_ms}})
                    .sort("ts", -1)
                    .limit(50)
                )

                # 5. Transform to output format
                slow_queries = []
                for doc in profile_docs:
                    slow_queries.append(
                        {
                            "timestamp": doc.get("ts"),
                            "operation": doc.get("op"),
                            "namespace": doc.get("ns"),
                            "duration_ms": doc.get("millis"),
                            "examined_docs": doc.get("execStats", {}).get("totalDocsExamined", 0),
                            "returned_docs": doc.get("execStats", {}).get("nReturned", 0),
                            "query": doc.get("command"),
                        }
                    )

                return slow_queries

            finally:
                # 6. Restore original profiling level
                try:
                    self._db.command("profile", original_level)
                except Exception as e:
                    print(f"Warning: Failed to restore profiling level: {e}")

        except Exception as e:
            raise QueryAnalysisError(f"Failed to get slow queries: {e}") from e

    def get_metrics(self) -> dict:
        """Get MongoDB engine metrics (version, etc)."""
        try:
            if not self._client:
                raise QueryAnalysisError("Not connected to MongoDB")
            server_info = self._client.server_info()
            return {
                "version": server_info.get("version"),
                "operating_system": server_info.get("os", {}).get("type"),
            }
        except Exception as e:
            raise QueryAnalysisError(f"Failed to get metrics: {e}") from e

    def get_engine_info(self) -> dict:
        """Get MongoDB engine information."""
        return {
            "engine": "mongodb",
            "driver": "pymongo",
            **self.get_metrics(),
        }
