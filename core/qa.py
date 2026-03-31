"""
core/qa.py - Immutable QA Inspector
"""
from pathlib import Path

from core.contracts import CONTRACTS
from core.models import Part, QAResult, QAStatus


def inspect(part: Part) -> QAResult:
    issues: list[str] = []
    contract = CONTRACTS.get(part.part_type)

    if contract is None:
        return QAResult(part=part, status=QAStatus.WARNING, issues=["No contract defined"])

    path: Path = part.file_path

    if not path.exists():
        return QAResult(part=part, status=QAStatus.FAIL, issues=[f"File not found: {path}"])

    if path.suffix.lower() not in contract.get("allowed_formats", []):
        issues.append(f"Format {path.suffix} not in {contract['allowed_formats']}")

    max_mb = contract.get("max_size_mb")
    if max_mb:
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > max_mb:
            issues.append(f"Size {size_mb:.1f}MB > {max_mb}MB limit")

    if any("not found" in i.lower() or "format" in i.lower() for i in issues):
        status = QAStatus.FAIL
    elif issues:
        status = QAStatus.WARNING
    else:
        status = QAStatus.PASS

    return QAResult(part=part, status=status, issues=issues)