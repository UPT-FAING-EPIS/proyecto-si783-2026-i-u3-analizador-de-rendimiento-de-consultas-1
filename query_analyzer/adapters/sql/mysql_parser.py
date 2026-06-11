"""MySQL EXPLAIN plan parser."""

import json
from typing import Any


class MySQLExplainParser:
    """Parseador especializado para salidas EXPLAIN de MySQL.

    Analiza planes de ejecución en formato JSON (EXPLAIN FORMAT=JSON) y
    extrae la estructura y métricas observadas por el motor.

    Métodos principales:
        - parse(): Parsea JSON de EXPLAIN y extrae métricas
        - normalize_plan(): Unifica la estructura para la interfaz
    """

    def parse(self, json_output: str) -> dict[str, Any]:
        """Parse EXPLAIN FORMAT=JSON output and extract metrics.

        Args:
            json_output: Complete EXPLAIN FORMAT=JSON output as string

        Returns:
            Dictionary with:
                - raw_json: Original JSON string
                - query_block: Parsed query block
                - tables_accessed: List of table access info
                - has_using_filesort: Whether external sort is used
                - has_using_temporary: Whether temporary table is used
                - has_full_scan: Whether full table scan exists
                - total_rows_examined: Total rows examined across all tables
        """
        try:
            data = json.loads(json_output)
        except json.JSONDecodeError:
            return self._empty_result()

        parsed = self._empty_result()
        parsed["raw_json"] = json_output

        if "query_block" not in data:
            return parsed

        query_block = data["query_block"]
        parsed["query_block"] = query_block

        self._extract_tables(query_block, parsed)

        return parsed

    def _empty_result(self) -> dict[str, Any]:
        """Create empty result dict with default values.

        Returns:
            Empty result dictionary with initialized fields
        """
        return {
            "raw_json": "",
            "query_block": {},
            "tables_accessed": [],
            "has_using_filesort": False,
            "has_using_temporary": False,
            "has_full_scan": False,
            "total_rows_examined": 0,
        }

    def _extract_tables(self, query_block: dict, result: dict) -> None:
        """Recursively extract table access information from query block.

        Args:
            query_block: Current query block dictionary
            result: Result accumulator dictionary
        """
        if "table" in query_block:
            table_info = query_block["table"]
            self._process_table(table_info, result)

        if "nested_loop" in query_block:
            for nested_item in query_block["nested_loop"]:
                self._extract_tables(nested_item, result)

        if "union_result" in query_block:
            union = query_block["union_result"]
            if "query_block" in union:
                self._extract_tables(union["query_block"], result)

        if "order_by" in query_block:
            order_items = query_block["order_by"]
            if isinstance(order_items, list):
                for item in order_items:
                    if isinstance(item, dict) and item.get("filesort") is True:
                        result["has_using_filesort"] = True

    def _process_table(self, table_info: dict, result: dict) -> None:
        """Process individual table access information.

        Args:
            table_info: Table information dictionary from EXPLAIN output
            result: Result accumulator dictionary
        """
        table_name = table_info.get("table_name", "unknown")
        access_type = table_info.get("access_type", "unknown").upper()
        key_used = table_info.get("key")
        rows_examined = table_info.get("rows_examined", 0)
        extra = table_info.get("extra", [])

        result["total_rows_examined"] += rows_examined

        is_full_scan = access_type == "ALL"
        if is_full_scan:
            result["has_full_scan"] = True

        if isinstance(extra, list):
            for extra_item in extra:
                if isinstance(extra_item, dict):
                    if extra_item.get("using_temporary_table") is True:
                        result["has_using_temporary"] = True
                    extra_desc = extra_item.get("description", "")
                    if "filesort" in extra_desc.lower():
                        result["has_using_filesort"] = True
                    if "temporary" in extra_desc.lower():
                        result["has_using_temporary"] = True
                elif isinstance(extra_item, str):
                    if "filesort" in extra_item.lower():
                        result["has_using_filesort"] = True
                    if "temporary" in extra_item.lower():
                        result["has_using_temporary"] = True

        result["tables_accessed"].append(
            {
                "table_name": table_name,
                "access_type": access_type,
                "key_used": key_used,
                "rows_examined": rows_examined,
                "is_full_scan": is_full_scan,
            }
        )

    def normalize_plan(self, plan: dict) -> dict:
        """Convert MySQL EXPLAIN plan to normalized format (engine-agnostic).

        Converts MySQL EXPLAIN FORMAT=JSON plan structure to a normalized format that can be
        used by renderers and integrations independently of the SQL engine.

        Args:
            plan: EXPLAIN output dictionary from MySQL

        Returns:
            Normalized plan node with keys:
                - node_type: str (mapped from access_type: ALL -> "Seq Scan", etc.)
                - table_name: str | None
                - actual_rows: int | None (mapped from rows_examined)
                - estimated_rows: int | None (mapped from rows)
                - actual_time_ms: float | None (not available in MySQL)
                - estimated_cost: float | None (not available in MySQL)
                - index_used: str | None (mapped from 'key' field)
                - filter_condition: str | None (extracted from 'filtered')
                - extra_info: list[str] (from 'extra' field, e.g., "Using filesort")
                - buffers: None (not available in MySQL)
                - children: list[dict] (normalized child nodes from 'nested_loop')
        """
        if not plan:
            return {}

        if "query_block" in plan and isinstance(plan["query_block"], dict):
            return self.normalize_plan(plan["query_block"])

        # Extract table info (node may already be a table payload)
        if isinstance(plan.get("table"), dict):
            table_data = plan["table"]
        elif "table_name" in plan:
            table_data = plan
        else:
            table_data = {}
        table_name = table_data.get("table_name")

        # Map MySQL access_type to standard node_type
        access_type = table_data.get("access_type", "UNKNOWN")
        node_type_map = {
            "ALL": "Seq Scan",
            "const": "Index Scan",
            "eq_ref": "Index Scan",
            "ref": "Index Scan",
            "range": "Index Scan",
            "index": "Index Scan",
            "index_merge": "Index Scan",
            "system": "Index Scan",
        }
        has_filesort = bool(plan.get("using_filesort") or table_data.get("using_filesort"))
        has_temporary = bool(
            plan.get("using_temporary_table") or table_data.get("using_temporary_table")
        )

        if has_filesort or has_temporary:
            node_type = "Sort"
        elif "nested_loop" in plan and not table_data:
            node_type = "Nested Loop"
        else:
            node_type = node_type_map.get(access_type, f"Scan({access_type})")

        # Extract row counts (MySQL JSON format)
        rows_examined = table_data.get("rows_examined_per_scan") or table_data.get("rows_examined")
        estimated_rows = table_data.get("rows_produced_per_join") or table_data.get("rows")

        # Extract index information
        index_used = table_data.get("key")

        # Extract extra information
        extra_info: list[str] = []
        if has_filesort:
            extra_info.append("Using filesort")
        if has_temporary:
            extra_info.append("Using temporary")
        extra_list = table_data.get("extra", [])
        if extra_list:
            for extra in extra_list:
                if "extra_info" in extra:
                    extra_info.append(extra["extra_info"])

        # Filter condition when available
        filter_condition = table_data.get("attached_condition")

        # Recursively normalize child nodes
        children: list[dict[str, Any]] = []

        ordering_operation = plan.get("ordering_operation")
        if isinstance(ordering_operation, dict):
            children.append(self.normalize_plan(ordering_operation))

        for nested_loop in plan.get("nested_loop", []):
            if isinstance(nested_loop, dict):
                child = self.normalize_plan(nested_loop)
                if child:
                    children.append(child)

        if not table_name:
            table_name = self._first_table_name(children)

        return {
            "node_type": node_type,
            "table_name": table_name,
            "actual_rows": rows_examined,
            "estimated_rows": estimated_rows,
            "actual_time_ms": None,  # Not available in MySQL EXPLAIN
            "estimated_cost": None,  # Not available in MySQL EXPLAIN
            "index_used": index_used,
            "filter_condition": filter_condition,
            "extra_info": extra_info,
            "buffers": None,  # Not available in MySQL
            "children": children,
        }

    def _first_table_name(self, children: list[dict[str, Any]]) -> str | None:
        """Get first available table name from descendant nodes."""
        for child in children:
            candidate = child.get("table_name")
            if candidate:
                return str(candidate)

            nested_children = child.get("children", [])
            if isinstance(nested_children, list):
                descendant = self._first_table_name(nested_children)
                if descendant:
                    return descendant

        return None
