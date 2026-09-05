"""Tests for reviewer.py — no network calls, no API keys needed."""

from app.ai_reviewer import Finding, ReviewResult, Severity
from app.reviewer import ReviewSummary, is_excluded, review_files


class FakeAIReviewer:
    """Stands in for AIReviewer so these tests never call a real API."""

    def __init__(self, findings_by_file=None):
        self.findings_by_file = findings_by_file or {}
        self.calls = []

    def review_file(self, filename, patch):
        self.calls.append(filename)
        return ReviewResult(findings=self.findings_by_file.get(filename, []))


DEFAULT_CONFIG = {
    "model": "gemini-3.8-flash",
    "severity_threshold": "SUGGESTION",
    "excluded_paths": ["*.lock", "package-lock.json"],
    "max_diff_lines": 5,
}


def make_finding(file="app.py", severity=Severity.CRITICAL):
    return Finding(
        file=file, severity=severity, issue="Test issue",
        explanation="Test explanation", suggested_fix="Test fix",
    )


def test_is_excluded_matches_glob():
    assert is_excluded("package-lock.json", ["package-lock.json"]) is True
    assert is_excluded("yarn.lock", ["*.lock"]) is True


def test_is_excluded_no_match():
    assert is_excluded("app.py", ["*.lock", "package-lock.json"]) is False


def test_review_files_skips_excluded_paths():
    ai_reviewer = FakeAIReviewer(findings_by_file={"package-lock.json": [make_finding()]})
    changed_files = [{"filename": "package-lock.json", "patch": "@@ -1 +1 @@\n-a\n+b\n"}]

    summary = review_files(changed_files, ai_reviewer, DEFAULT_CONFIG)

    assert summary.findings == []
    assert ai_reviewer.calls == []  # never even called for an excluded file


def test_review_files_skips_oversized_diff():
    huge_patch = "\n".join(["+line"] * 20)  # more lines than max_diff_lines=5
    changed_files = [{"filename": "big.py", "patch": huge_patch}]
    ai_reviewer = FakeAIReviewer()

    summary = review_files(changed_files, ai_reviewer, DEFAULT_CONFIG)

    assert summary.skipped_files == ["big.py"]
    assert ai_reviewer.calls == []


def test_review_files_collects_findings():
    finding = make_finding(file="app.py", severity=Severity.WARNING)
    ai_reviewer = FakeAIReviewer(findings_by_file={"app.py": [finding]})
    changed_files = [{"filename": "app.py", "patch": "@@ -1 +1 @@\n-old\n+new\n"}]

    summary = review_files(changed_files, ai_reviewer, DEFAULT_CONFIG)

    assert summary.findings == [finding]
    assert ai_reviewer.calls == ["app.py"]


def test_review_files_skips_files_with_no_patch():
    changed_files = [{"filename": "renamed.py", "patch": None}]
    ai_reviewer = FakeAIReviewer()

    summary = review_files(changed_files, ai_reviewer, DEFAULT_CONFIG)

    assert summary.findings == []
    assert ai_reviewer.calls == []


def test_meets_threshold_true_when_severity_present():
    summary = ReviewSummary(findings=[make_finding(severity=Severity.CRITICAL)], skipped_files=[])
    assert summary.meets_threshold("CRITICAL") is True


def test_meets_threshold_false_when_below():
    summary = ReviewSummary(findings=[make_finding(severity=Severity.SUGGESTION)], skipped_files=[])
    assert summary.meets_threshold("CRITICAL") is False


def test_to_markdown_no_issues():
    summary = ReviewSummary(findings=[], skipped_files=[])
    assert "No issues found." in summary.to_markdown()


def test_to_markdown_includes_finding_details():
    finding = make_finding(file="auth.py", severity=Severity.CRITICAL)
    summary = ReviewSummary(findings=[finding], skipped_files=[])
    markdown = summary.to_markdown()

    assert "auth.py" in markdown
    assert "CRITICAL" in markdown
    assert "Test issue" in markdown