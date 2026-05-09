"""Helper functions for building plan trees from EXPLAIN output.

This module provides utilities for parsing and structuring query execution plans
from various database engines into a unified PlanNode tree representation.
"""

from typing import Any

from .models import PlanNode


def build_plan_tree(raw_plan_dict: dict[str, Any], node_type: str = "root") -> PlanNode | None:
    """Build PlanNode tree from raw EXPLAIN plan dictionary.

    Handles generic plan structure that works across different SQL databases
    (PostgreSQL, MySQL, etc.) by extracting common fields.

    Args:
        raw_plan_dict: Raw EXPLAIN plan as dictionary
        node_type: Node type for the root (default: "root")

    Returns:
        PlanNode tree or None if plan is empty

    Raises:
        ValueError: If plan structure is invalid
    """
    if not raw_plan_dict:
        return None

    actual_node_type = (
        raw_plan_dict.get("Node Type")
        or raw_plan_dict.get("type")
        or raw_plan_dict.get("operation")
        or node_type
    )

    cost = raw_plan_dict.get("Total Cost") or raw_plan_dict.get("cost")
    estimated_rows = raw_plan_dict.get("Estimated Rows") or raw_plan_dict.get("estimated_rows")
    actual_rows = raw_plan_dict.get("Actual Rows") or raw_plan_dict.get("actual_rows")
    actual_time = (
        raw_plan_dict.get("Actual Total Time")
        or raw_plan_dict.get("actual_time_ms")
        or raw_plan_dict.get("Actual Time")
    )

    if isinstance(cost, (int, float)):
        cost = float(cost)
    if isinstance(estimated_rows, (int, float)):
        estimated_rows = int(estimated_rows)
    if isinstance(actual_rows, (int, float)):
        actual_rows = int(actual_rows)
    if isinstance(actual_time, (int, float)):
        actual_time_ms = float(actual_time)
    else:
        actual_time_ms = None

    children: list[PlanNode] = []
    plans = raw_plan_dict.get("Plans") or raw_plan_dict.get("children") or []
    for child_plan in plans:
        if isinstance(child_plan, dict):
            child_node = build_plan_tree(child_plan)
            if child_node:
                children.append(child_node)

    properties: dict[str, Any] = {}
    for key, value in raw_plan_dict.items():
        if key not in {
            "Node Type",
            "type",
            "operation",
            "Total Cost",
            "cost",
            "Estimated Rows",
            "estimated_rows",
            "Actual Rows",
            "actual_rows",
            "Actual Total Time",
            "actual_time_ms",
            "Actual Time",
            "Plans",
            "children",
        }:
            properties[key] = value

    return PlanNode(
        node_type=actual_node_type,
        cost=cost,
        estimated_rows=estimated_rows,
        actual_rows=actual_rows,
        actual_time_ms=actual_time_ms,
        children=children,
        properties=properties,
    )
