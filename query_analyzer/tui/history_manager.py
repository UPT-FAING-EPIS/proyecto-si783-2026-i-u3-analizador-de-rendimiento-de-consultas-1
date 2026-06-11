"""History manager for storing and retrieving past query analyses."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    report: QueryAnalysisReport
    profile_name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    notes: str = ""

    @property
    def id(self) -> str:
        """Generate unique ID based on timestamp."""
        return self.created_at.isoformat()

    def query_preview(self, max_len: int = 60) -> str:
        """Get query preview text."""
        single_line = " ".join(self.query.split())
        if len(single_line) > max_len:
            return single_line[: max_len - 3] + "..."
        return single_line


class HistoryManager:
    """Persistent history manager for query analyses.

    Stores analysis records in memory and persists them to disk per profile.
    """

    def __init__(self, max_size: int = 100, storage_dir: Path | None = None) -> None:
        """Initialize history manager.

        Args:
            max_size: Maximum number of records to keep per profile
            storage_dir: Optional custom storage folder for tests
        """
        self._records: list[AnalysisRecord] = []
        self._max_size = max_size
        self._storage_dir = storage_dir or (Path.home() / ".query-analyzer" / "history")
        self._load_all()

    @staticmethod
    def _sanitize_profile_name(profile_name: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", profile_name.strip())
        cleaned = re.sub(r"_+", "_", cleaned).strip("._")
        return cleaned or "default"

    def _profile_path(self, profile_name: str) -> Path:
        safe_name = self._sanitize_profile_name(profile_name)
        return self._storage_dir / f"{safe_name}.json"

    def _load_all(self) -> None:
        self._records = []
        if not self._storage_dir.exists():
            return

        for path in self._storage_dir.glob("*.json"):
            self._records.extend(self._load_profile_file(path))

        self._records.sort(key=lambda record: record.created_at)

    def _load_profile_file(self, path: Path) -> list[AnalysisRecord]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                raise ValueError("History file must contain a list")
            return [self._deserialize_record(item) for item in payload if isinstance(item, dict)]
        except Exception:
            broken = path.with_name(
                f"{path.stem}.broken-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            try:
                path.replace(broken)
            except Exception:
                pass
            return []

    @staticmethod
    def _deserialize_record(item: dict[str, Any]) -> AnalysisRecord:
        created_at_raw = item.get("created_at")
        created_at = (
            datetime.fromisoformat(created_at_raw)
            if isinstance(created_at_raw, str)
            else datetime.now(UTC)
        )
        report = QueryAnalysisReport.model_validate(item.get("report", {}))

        return AnalysisRecord(
            query=str(item.get("query", "")),
            report=report,
            profile_name=str(item.get("profile_name", "default")),
            created_at=created_at,
            notes=str(item.get("notes", "")),
        )

    @staticmethod
    def _serialize_record(record: AnalysisRecord) -> dict[str, Any]:
        return {
            "query": record.query,
            "report": record.report.model_dump(mode="json"),
            "profile_name": record.profile_name,
            "created_at": record.created_at.isoformat(),
            "notes": record.notes,
        }

    def _persist_profile(self, profile_name: str) -> None:
        profile_records = [r for r in self._records if r.profile_name == profile_name]
        if len(profile_records) > self._max_size:
            profile_records = profile_records[-self._max_size :]
            self._records = [r for r in self._records if r.profile_name != profile_name]
            self._records.extend(profile_records)
            self._records.sort(key=lambda r: r.created_at)

        self._storage_dir.mkdir(parents=True, exist_ok=True)
        path = self._profile_path(profile_name)
        temp_path = path.with_suffix(".json.tmp")
        payload = [self._serialize_record(record) for record in profile_records]
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_path.replace(path)

    def add(
        self,
        query: str,
        report: QueryAnalysisReport,
        profile_name: str,
        notes: str = "",
    ) -> AnalysisRecord:
        """Add a new analysis record to history."""
        record = AnalysisRecord(
            query=query,
            report=report,
            profile_name=profile_name,
            notes=notes,
        )
        self._records.append(record)
        self._records.sort(key=lambda r: r.created_at)
        self._persist_profile(profile_name)
        return record

    def get(self, index: int) -> AnalysisRecord | None:
        """Get record by index from internal chronological list."""
        try:
            return self._records[index]
        except IndexError:
            return None

    def get_all(self) -> list[AnalysisRecord]:
        """Get all records in reverse chronological order."""
        return list(reversed(self._records))

    def get_all_for_profile(self, profile_name: str) -> list[AnalysisRecord]:
        """Get profile records in reverse chronological order."""
        records = [record for record in self._records if record.profile_name == profile_name]
        return list(reversed(records))

    def search_by_query(self, query_text: str) -> list[AnalysisRecord]:
        """Search records by query text (substring match)."""
        query_lower = query_text.lower()
        matches = [record for record in self._records if query_lower in record.query.lower()]
        return list(reversed(matches))

    def search_by_profile(self, profile_name: str) -> list[AnalysisRecord]:
        """Search records by profile name."""
        matches = [record for record in self._records if record.profile_name == profile_name]
        return list(reversed(matches))

    def search_by_engine(self, engine: str) -> list[AnalysisRecord]:
        """Search records by database engine."""
        matches = [record for record in self._records if record.report.engine == engine]
        return list(reversed(matches))

    def clear(self) -> None:
        """Clear all history and remove all history files."""
        self._records.clear()
        if self._storage_dir.exists():
            for path in self._storage_dir.glob("*.json"):
                path.unlink()

    def clear_profile(self, profile_name: str) -> None:
        """Clear history only for one profile."""
        self._records = [record for record in self._records if record.profile_name != profile_name]
        path = self._profile_path(profile_name)
        if path.exists():
            path.unlink()

    def delete(self, index: int) -> bool:
        """Delete a single record by index."""
        try:
            record = self._records.pop(index)
            self._persist_profile(record.profile_name)
            return True
        except IndexError:
            return False

    def delete_record(self, record: AnalysisRecord) -> bool:
        """Delete a specific record and persist its profile file."""
        for idx, existing in enumerate(self._records):
            if (
                existing.profile_name == record.profile_name
                and existing.created_at == record.created_at
                and existing.query == record.query
            ):
                removed = self._records.pop(idx)
                self._persist_profile(removed.profile_name)
                return True
        return False

    def size(self) -> int:
        """Get current number of records."""
        return len(self._records)

    def is_empty(self) -> bool:
        """Check if history is empty."""
        return len(self._records) == 0

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about history."""
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


_instance: HistoryManager | None = None


def get_history_manager() -> HistoryManager:
    """Get or create global history manager instance."""
    global _instance
    if _instance is None:
        _instance = HistoryManager()
    return _instance


def reset_history_manager() -> None:
    """Reset global history manager (useful for testing)."""
    global _instance
    _instance = None
