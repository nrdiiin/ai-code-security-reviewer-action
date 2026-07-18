"""Tests for format_pr_comment.py."""

import json
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from format_pr_comment import (
    count_by_severity,
    format_findings_table,
    format_summary,
    generate_comment,
    load_findings,
    MARKER,
)


@pytest.fixture
def sample_findings():
    return [
        {"severity": "critical", "file": "auth.py", "message": "SQL injection vulnerability", "rule_id": "sql-injection", "line": 10, "column": 4},
        {"severity": "high", "file": "api.py", "message": "Missing authentication check", "rule_id": "missing-auth", "line": 22, "column": 1},
        {"severity": "medium", "file": "utils.py", "message": "Unsafe deserialization", "rule_id": "unsafe-deser", "line": 5, "column": 8},
        {"severity": "low", "file": "config.py", "message": "Hardcoded default port", "rule_id": "hardcoded-port", "line": 3, "column": 12},
        {"severity": "info", "file": "main.py", "message": "Unused import", "rule_id": "unused-import", "line": 1, "column": 1},
    ]


@pytest.fixture
def json_file(sample_findings, tmp_path):
    """JSON matching real `aicsr scan --format json` output structure."""
    data = {
        "total": len(sample_findings),
        "summary": {"critical": 1, "high": 1, "medium": 1, "low": 1, "info": 1},
        "findings": sample_findings,
    }
    path = tmp_path / "results.json"
    path.write_text(json.dumps(data))
    return str(path)


@pytest.fixture
def empty_json_file(tmp_path):
    data = {"total": 0, "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}, "findings": []}
    path = tmp_path / "results.json"
    path.write_text(json.dumps(data))
    return str(path)


class TestLoadFindings:
    def test_loads_findings(self, json_file):
        total, findings = load_findings(json_file)
        assert total == 5
        assert len(findings) == 5

    def test_loads_empty(self, empty_json_file):
        total, findings = load_findings(empty_json_file)
        assert total == 0
        assert len(findings) == 0

    def test_missing_key(self, tmp_path):
        path = tmp_path / "no_key.json"
        path.write_text(json.dumps({"other": "data"}))
        total, findings = load_findings(str(path))
        assert findings == []
        assert total == 0

    def test_total_falls_back_to_findings_length(self, tmp_path):
        """If 'total' key is missing, falls back to len(findings)."""
        path = tmp_path / "no_total.json"
        path.write_text(json.dumps({"findings": [{"severity": "low", "message": "x"}]}))
        total, findings = load_findings(str(path))
        assert total == 1
        assert len(findings) == 1


class TestCountBySeverity:
    def test_counts_all_severities(self, sample_findings):
        counts = count_by_severity(sample_findings)
        assert counts["critical"] == 1
        assert counts["high"] == 1
        assert counts["medium"] == 1
        assert counts["low"] == 1
        assert counts["info"] == 1

    def test_empty_findings(self):
        counts = count_by_severity([])
        assert counts == {}

    def test_multiple_same_severity(self):
        findings = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "low"},
        ]
        counts = count_by_severity(findings)
        assert counts["high"] == 2
        assert counts["low"] == 1


class TestFormatSummary:
    def test_summary_with_findings(self):
        counts = {"critical": 2, "high": 3, "low": 1}
        summary = format_summary(counts, 6)
        assert "🔴 2 critical" in summary
        assert "🟠 3 high" in summary
        assert "🔵 1 low" in summary

    def test_summary_empty(self):
        summary = format_summary({}, 0)
        assert summary == ""

    def test_summary_order(self):
        counts = {"info": 1, "critical": 1}
        summary = format_summary(counts, 2)
        # critical should come before info
        crit_pos = summary.index("critical")
        info_pos = summary.index("info")
        assert crit_pos < info_pos


class TestFormatFindingsTable:
    def test_table_has_header(self, sample_findings):
        table = format_findings_table(sample_findings)
        assert "| Severity | File | Description |" in table
        assert "|----------|------|-------------|" in table

    def test_table_limits_to_10(self):
        findings = [{"severity": "low", "file": f"f{i}.py", "message": "d"} for i in range(20)]
        table = format_findings_table(findings)
        # Count data rows (exclude header + separator)
        rows = [line for line in table.split("\n") if line.startswith("|") and "---" not in line and "Severity" not in line]
        assert len(rows) == 10

    def test_table_sorted_by_severity(self, sample_findings):
        table = format_findings_table(sample_findings)
        lines = [line for line in table.split("\n") if line.startswith("|") and "---" not in line and "Severity" not in line]
        # First row should be critical
        assert "critical" in lines[0]

    def test_empty_findings(self):
        table = format_findings_table([])
        assert table == ""

    def test_truncates_long_descriptions(self):
        findings = [{"severity": "low", "file": "x.py", "message": "A" * 100}]
        table = format_findings_table(findings)
        assert "A" * 77 + "..." in table

    def test_uses_message_field(self):
        """Verify it reads 'message' not 'description'."""
        findings = [{"severity": "high", "file": "test.py", "message": "Found via message field"}]
        table = format_findings_table(findings)
        assert "Found via message field" in table

    def test_falls_back_when_message_missing(self):
        """Graceful fallback if 'message' key is absent."""
        findings = [{"severity": "high", "file": "test.py"}]
        table = format_findings_table(findings)
        assert "No description" in table


class TestGenerateComment:
    def test_contains_marker(self, json_file):
        comment = generate_comment(json_file)
        assert MARKER in comment

    def test_no_findings_message(self, empty_json_file):
        comment = generate_comment(empty_json_file)
        assert "No security findings" in comment
        assert "✅" in comment

    def test_has_findings(self, json_file):
        comment = generate_comment(json_file)
        assert "5 finding(s)" in comment
        assert "Top Findings" in comment

    def test_has_security_link_with_repo(self, json_file):
        comment = generate_comment(json_file, repo="owner/repo")
        assert "https://github.com/owner/repo/security/code-scanning" in comment

    def test_no_repo_fallback(self, json_file):
        comment = generate_comment(json_file, repo="")
        assert "Security" in comment

    def test_uses_total_from_json(self, tmp_path):
        """total field in JSON should be used even if findings list is shorter."""
        # Edge case: total says 100 but only 3 findings in file (truncated?)
        data = {
            "total": 100,
            "summary": {"critical": 50, "high": 50, "medium": 0, "low": 0, "info": 0},
            "findings": [
                {"severity": "critical", "file": "a.py", "message": "m1"},
                {"severity": "high", "file": "b.py", "message": "m2"},
                {"severity": "critical", "file": "c.py", "message": "m3"},
            ],
        }
        path = tmp_path / "results.json"
        path.write_text(json.dumps(data))
        comment = generate_comment(str(path))
        # Should show total from JSON, not len(findings)
        assert "100 finding(s)" in comment


class TestMain:
    def test_main_writes_output(self, json_file, tmp_path):
        out = tmp_path / "comment.md"
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "format_pr_comment.py"),
                "--input", json_file,
                "--output", str(out),
                "--repo", "test/repo",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert out.exists()
        content = out.read_text()
        assert MARKER in content

    def test_main_missing_input(self, tmp_path):
        out = tmp_path / "comment.md"
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent.parent / "scripts" / "format_pr_comment.py"),
                "--input", "/nonexistent/file.json",
                "--output", str(out),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert out.exists()
        assert "No scan results" in out.read_text()
