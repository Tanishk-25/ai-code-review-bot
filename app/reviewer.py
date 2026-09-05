"""Combines GitHub data and AI findings, applies config rules. No network calls of its own."""

import fnmatch
from dataclasses import dataclass
from typing import List

import yaml

from app.ai_reviewer import Finding, Severity

DEFAULT_CONFIG = {
    "model": "gemini-3.8-flash",
    "severity_threshold": "SUGGESTION",
    "excluded_paths": [],
    "max_diff_lines": 300,
}

SEVERITY_ORDER = {Severity.SUGGESTION: 0, Severity.WARNING: 1, Severity.CRITICAL: 2}


def load_config(path: str = ".aicr.yml") -> dict:
    try:
        with open(path) as f:
            user_config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        user_config = {}
    return {**DEFAULT_CONFIG, **user_config}


def is_excluded(filename: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)


@dataclass
class ReviewSummary:
    findings: List[Finding]
    skipped_files: List[str]

    def counts(self) -> dict:
        counts = {"CRITICAL": 0, "WARNING": 0, "SUGGESTION": 0}
        for f in self.findings:
            counts[f.severity.value] += 1
        return counts

    def meets_threshold(self, threshold: str) -> bool:
        threshold_level = SEVERITY_ORDER[Severity(threshold)]
        return any(SEVERITY_ORDER[f.severity] >= threshold_level for f in self.findings)

    def to_markdown(self) -> str:
        counts = self.counts()
        lines = [
            "## AI Code Review Summary",
            "",
            f"**Critical:** {counts['CRITICAL']}  |  **Warnings:** {counts['WARNING']}  |  **Suggestions:** {counts['SUGGESTION']}",
            "",
        ]
        if not self.findings:
            lines.append("No issues found.")
        else:
            lines.append("### Findings")
            for f in self.findings:
                location = f.file + (f" (line {f.line})" if f.line else "")
                lines.append(f"- **[{f.severity.value}]** `{location}` — {f.issue}")
                lines.append(f"  - {f.explanation}")
                lines.append(f"  - Suggested fix: {f.suggested_fix}")
        if self.skipped_files:
            lines.append("")
            lines.append("### Skipped (diff too large)")
            for name in self.skipped_files:
                lines.append(f"- {name}")
        return "\n".join(lines)


def review_files(changed_files: List[dict], ai_reviewer, config: dict) -> ReviewSummary:
    """changed_files: list of dicts from github_client.get_changed_files()."""
    findings: List[Finding] = []
    skipped: List[str] = []

    for f in changed_files:
        filename = f["filename"]
        patch = f.get("patch")

        if is_excluded(filename, config["excluded_paths"]):
            continue
        if not patch:
            continue  # e.g. pure rename or binary file — nothing to review

        diff_lines = patch.count("\n") + 1
        if diff_lines > config["max_diff_lines"]:
            skipped.append(filename)
            continue

        result = ai_reviewer.review_file(filename, patch)
        findings.extend(result.findings)

    return ReviewSummary(findings=findings, skipped_files=skipped)