"""PostgreSQL EXPLAIN plan parser and analyzer."""

from typing import Any


class PostgreSQLExplainParser:
    """Parseador especializado para salidas EXPLAIN de PostgreSQL.

    Analiza planes de ejecución en formato JSON (EXPLAIN ANALYZE, BUFFERS, FORMAT JSON)
    para extraer métricas de rendimiento y detectar anti-patrones. Recorre recursivamente
    el árbol de planes, calcula costos estimados vs. actuales, identifica operaciones
    costosas (sequential scans, index operations, joins), y genera una puntuación de
    optimización (0-100) basada en la estructura del plan.

    Atributos:
        seq_scan_threshold: Número de filas en tabla para considerar Seq Scan como
            posible anti-patrón (default: 10000).
    """

    def __init__(self, seq_scan_threshold: int = 10000) -> None:
        """Initialize parser with configurable thresholds.

        Args:
            seq_scan_threshold: Table row count threshold for Seq Scan warning
                (default: 10000)
        """
        self.seq_scan_threshold = seq_scan_threshold

    def parse(self, explain_json: dict[str, Any]) -> dict[str, Any]:
        """Parse EXPLAIN output and extract all metrics.

        Args:
            explain_json: Complete EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) output

        Returns:
            Dictionary with:
                - planning_time_ms: Planning time
                - execution_time_ms: Total execution time
                - total_cost: Estimated total cost
                - actual_rows_total: Total actual rows returned
                - plan_rows_total: Total estimated rows
                - node_count: Number of nodes in plan tree
                - most_expensive_node: Node with highest Total Cost
                - buffer_stats: Shared hit/read statistics
                - scan_nodes: All Seq/Index scan nodes
                - join_nodes: All join operation nodes
                - all_nodes: Flat list of all nodes
        """
        plan = explain_json.get("Plan", {})

        # Collect all nodes via recursive traversal
        all_nodes: list[dict[str, Any]] = []
        self._traverse_plan_tree(plan, all_nodes)

        # Extract basic metrics
        planning_time_ms = float(explain_json.get("Planning Time", 0.0))
        execution_time_ms = float(explain_json.get("Execution Time", 0.0))

        # Aggregate metrics across all nodes
        total_cost = float(plan.get("Total Cost", 0.0))
        actual_rows_total = self._sum_actual_rows(all_nodes)
        plan_rows_total = self._sum_plan_rows(all_nodes)

        # Find most expensive node
        most_expensive = self._find_most_expensive_node(all_nodes)

        # Buffer statistics
        buffer_stats = self._aggregate_buffer_stats(all_nodes)

        # Categorize nodes by type
        scan_nodes = [n for n in all_nodes if "Scan" in n.get("Node Type", "")]
        join_nodes = [
            n for n in all_nodes if any(j in n.get("Node Type", "") for j in ["Join", "Hash"])
        ]

        return {
            "planning_time_ms": planning_time_ms,
            "execution_time_ms": execution_time_ms,
            "total_cost": total_cost,
            "actual_rows_total": actual_rows_total,
            "plan_rows_total": plan_rows_total,
            "node_count": len(all_nodes),
            "most_expensive_node": most_expensive,
            "buffer_stats": buffer_stats,
            "scan_nodes": scan_nodes,
            "join_nodes": join_nodes,
            "all_nodes": all_nodes,
        }

    def _traverse_plan_tree(
        self, node: dict[str, Any], all_nodes: list[dict[str, Any]], depth: int = 0
    ) -> None:
        """Recursively traverse plan tree, collecting all nodes.

        Args:
            node: Current plan node
            all_nodes: Accumulator list for all nodes
            depth: Current tree depth (for debugging)
        """
        if not node:
            return

        # Add current node to list with depth info
        node_copy = dict(node)
        node_copy["_depth"] = depth
        all_nodes.append(node_copy)

        # Recursively process child plans
        sub_plans = node.get("Plans", [])
        for sub_plan in sub_plans:
            self._traverse_plan_tree(sub_plan, all_nodes, depth + 1)

    def _sum_actual_rows(self, nodes: list[dict[str, Any]]) -> int:
        """Sum actual rows across all leaf nodes (nodes without children)."""
        # Count actual rows from nodes that don't have Plans array
        # (leaf nodes in the tree)
        total = 0
        for node in nodes:
            if "Plans" not in node or not node["Plans"]:
                total += int(node.get("Actual Rows", 0))
        return total

    def _sum_plan_rows(self, nodes: list[dict[str, Any]]) -> int:
        """Sum plan rows across all leaf nodes."""
        total = 0
        for node in nodes:
            if "Plans" not in node or not node["Plans"]:
                total += int(node.get("Plan Rows", 0))
        return total

    def _find_most_expensive_node(self, nodes: list[dict[str, Any]]) -> dict[str, Any]:
        """Find node with highest Total Cost.

        Returns dict with node info including cost and actual time.
        """
        if not nodes:
            return {}

        most_expensive = max(nodes, key=lambda n: float(n.get("Total Cost", 0)))

        return {
            "type": most_expensive.get("Node Type", "Unknown"),
            "cost": float(most_expensive.get("Total Cost", 0)),
            "actual_time": float(most_expensive.get("Actual Total Time", 0)),
            "actual_rows": int(most_expensive.get("Actual Rows", 0)),
            "plan_rows": int(most_expensive.get("Plan Rows", 0)),
        }

    def _aggregate_buffer_stats(self, nodes: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate buffer hit/read statistics across all nodes.

        Returns:
            Dict with shared_hit_total, shared_read_total, and cache_miss_rate
        """
        shared_hit = 0
        shared_read = 0

        for node in nodes:
            buffers = node.get("Buffers", {})
            if isinstance(buffers, dict):
                shared_hit += int(buffers.get("Shared Hit", 0))
                shared_read += int(buffers.get("Shared Read", 0))

        total_accesses = shared_hit + shared_read
        cache_miss_rate = 0.0
        if total_accesses > 0:
            cache_miss_rate = shared_read / total_accesses

        return {
            "shared_hit_total": shared_hit,
            "shared_read_total": shared_read,
            "total_accesses": total_accesses,
            "cache_miss_rate": cache_miss_rate,
        }

    def _calculate_row_divergence(self, plan_rows: int, actual_rows: int) -> float:
        """Calculate row estimate divergence: |actual - plan| / plan.

        Returns:
            Float in [0, inf). 0 = perfect estimate, 1.0 = 100% divergence, etc.
        """
        if plan_rows == 0:
            return float("inf") if actual_rows > 0 else 0.0
        return abs(actual_rows - plan_rows) / plan_rows

    def normalize_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Convert PostgreSQL EXPLAIN plan to normalized format (engine-agnostic).

        Converts PostgreSQL-specific plan structure to a normalized format that can be
        used by renderers and integrations independently of the SQL engine.

        Args:
            plan: Single node from EXPLAIN (ANALYZE, FORMAT JSON) output

        Returns:
            Normalized plan node with keys:
                - node_type: str (e.g., "Seq Scan", "Index Scan", "Nested Loop")
                - table_name: str | None
                - actual_rows: int | None
                - estimated_rows: int | None
                - actual_time_ms: float | None
                - estimated_cost: float | None
                - index_used: str | None
                - filter_condition: str | None
                - extra_info: list[str]
                - buffers: dict | None
                - children: list[dict] (normalized child nodes)
        """
        if not plan:
            return {}

        # Extract node type
        node_type = plan.get("Node Type", "Unknown")

        # Extract table/index information
        table_name = plan.get("Relation Name")
        index_name = plan.get("Index Name")

        # Extract row counts
        actual_rows = plan.get("Actual Rows")
        estimated_rows = plan.get("Plan Rows")

        # Extract timing
        actual_time_ms = plan.get("Actual Total Time")
        estimated_cost = plan.get("Total Cost")

        # Extract filter condition (if present)
        filter_condition = plan.get("Filter")

        # Index info: either Index Name or None
        index_used = index_name

        # Extra info (PostgreSQL-specific details)
        extra_info = []
        if plan.get("Rows Removed by Filter"):
            extra_info.append(f"Rows Removed: {plan['Rows Removed by Filter']}")
        if plan.get("Rows Removed by Index Recheck"):
            extra_info.append("Index Recheck")

        # Buffer statistics
        buffers = plan.get("Buffers")

        # Recursively normalize child nodes
        children = []
        for child_plan in plan.get("Plans", []):
            children.append(self.normalize_plan(child_plan))

        return {
            "node_type": node_type,
            "table_name": table_name,
            "actual_rows": actual_rows,
            "estimated_rows": estimated_rows,
            "actual_time_ms": actual_time_ms,
            "estimated_cost": estimated_cost,
            "index_used": index_used,
            "filter_condition": filter_condition,
            "extra_info": extra_info,
            "buffers": buffers,
            "children": children,
        }
