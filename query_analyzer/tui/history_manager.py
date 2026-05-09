"""History manager for storing and retrieving past query analyses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from query_analyzer.adapters.models import QueryAnalysisReport


@dataclass
class AnalysisRecord:
    """Record of a single analysis execution.

    Attributes:
        query: The SQL query that was analyzed
        report: The analysis report
        profile_name: The database profile used
        created_at: When the analysis was created
        notes: Optional user notes about the analysis
    """

    query: str
    """The SQL query that was analyzed"""

    report: QueryAnalysisReport
    """The analysis report"""

    profile_name: str
    """The database profile used"""

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """When the analysis was created (UTC)"""

    notes: str = ""
    """Optional user notes about the analysis"""

    @property
    def id(self) -> str:
        """Generate unique ID based on timestamp."""
        return self.created_at.isoformat()

    def query_preview(self, max_len: int = 60) -> str:
        """Get query preview text.

        Args:
            max_len: Maximum length of preview

        Returns:
            Truncated query text
        """
        single_line = " ".join(self.query.split())
        if len(single_line) > max_len:
            return single_line[:max_len - 3] + "..."
        return single_line


class HistoryManager:
    """In-memory history manager for query analyses.

    Stores analysis records in memory during the session.
    Records are lost when the application exits (by design).

    Features:
    - Add analysis records
    - Retrieve by index or query
    - Search by query text or profile
    - Clear history
    - Max size limit to prevent memory bloat
    """

    def __init__(self, max_size: int = 100) -> None:
        """Initialize history manager.

        Args:
            max_size: Maximum number of records to keep (default 100)
        """
        self._records: list[AnalysisRecord] = []
        self._max_size = max_size
        self._current_index = 0

    def add(
        self,
        query: str,
        report: QueryAnalysisReport,
        profile_name: str,
        notes: str = "",
    ) -> AnalysisRecord:
        """Add a new analysis record to history.

        Args:
            query: The SQL query
            report: The analysis report
            profile_name: The database profile used
            notes: Optional user notes

        Returns:
            The created AnalysisRecord
        """
        record = AnalysisRecord(
            query=query,
            report=report,
            profile_name=profile_name,
            notes=notes,
        )

        self._records.append(record)

        # Enforce max size limit
        if len(self._records) > self._max_size:
            self._records.pop(0)

        return record

    def get(self, index: int) -> AnalysisRecord | None:
        """Get record by index.

        Args:
            index: Index of record (can be negative for relative indexing)

        Returns:
            The AnalysisRecord or None if not found
        """
        try:
            return self._records[index]
        except IndexError:
            return None

    def get_all(self) -> list[AnalysisRecord]:
        """Get all records in reverse chronological order.

        Returns:
            List of AnalysisRecord objects (newest first)
        """
        return list(reversed(self._records))

    def search_by_query(self, query_text: str) -> list[AnalysisRecord]:
        """Search records by query text (substring match).

        Args:
            query_text: Text to search for in queries

        Returns:
            List of matching AnalysisRecord objects (newest first)
        """
        query_lower = query_text.lower()
        matches = [
            r for r in self._records if query_lower in r.query.lower()
        ]
        return list(reversed(matches))

    def search_by_profile(self, profile_name: str) -> list[AnalysisRecord]:
        """Search records by profile name.

        Args:
            profile_name: Profile name to search for

        Returns:
            List of matching AnalysisRecord objects (newest first)
        """
        matches = [
            r for r in self._records if r.profile_name == profile_name
        ]
        return list(reversed(matches))

    def search_by_engine(self, engine: str) -> list[AnalysisRecord]:
        """Search records by database engine.

        Args:
            engine: Engine name to search for

        Returns:
            List of matching AnalysisRecord objects (newest first)
        """
        matches = [
            r for r in self._records if r.report.engine == engine
        ]
        return list(reversed(matches))

    def clear(self) -> None:
        """Clear all history."""
        self._records.clear()

    def delete(self, index: int) -> bool:
        """Delete a single record by index.

        Args:
            index: Index of record to delete

        Returns:
            True if deleted, False if index not found
        """
        try:
            self._records.pop(index)
            return True
        except IndexError:
            return False

    def size(self) -> int:
        """Get current number of records.

        Returns:
            Number of records in history
        """
        return len(self._records)

    def is_empty(self) -> bool:
        """Check if history is empty.

        Returns:
            True if no records, False otherwise
        """
        return len(self._records) == 0

    def get_stats(self) -> dict[str, int]:
        """Get statistics about history.

        Returns:
            Dictionary with stats: total_records, by_engine, by_profile
        """
        by_engine: dict[str, int] = {}
        by_profile: dict[str, int] = {}

        for record in self._records:
            engine = record.report.engine
            by_engine[engine] = by_engine.get(engine, 0) + 1

            profile = record.profile_name
            by_profile[profile] = by_profile.get(profile, 0) + 1

        return {
            "total_records": len(self._records),
            "by_engine": by_engine,
            "by_profile": by_profile,
        }


# Global singleton instance
_instance: HistoryManager | None = None


def get_history_manager() -> HistoryManager:
    """Get or create global history manager instance.

    Returns:
        The global HistoryManager instance
    """
    global _instance
    if _instance is None:
        _instance = HistoryManager()
    return _instance


def reset_history_manager() -> None:
    """Reset global history manager (useful for testing)."""
    global _instance
    _instance = None
