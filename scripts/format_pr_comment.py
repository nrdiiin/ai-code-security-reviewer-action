#!/usr/bin/env python3
"""Format scan results (JSON) into a Markdown PR comment."""

import argparse
import json
from pathlib import Path

MARKER = "<!-- aicsr-scan-comment -->"

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
    "info": "⚪",
}

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def load_findings(json_path: str) -> tuple[int, list[dict]]:
    """Load findings from a JSON scan result file.

    Returns (total, findings). Uses 'total' from JSON if present,
    otherwise falls back to len(findings).
    """
    with open(json_path) as f:
        data = json.load(f)
    findings = data.get("findings", [])
    total = data.get("total", len(findings))
    return total, findings


def count_by_severity(findings: list[dict]) -> dict[str, int]:
    """Count findings grouped by severity."""
    counts: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "info").lower()
        counts[sev] = counts.get(sev, 0) + 1
    return counts


def format_summary(counts: dict[str, int], total: int) -> str:
    """Format the severity summary line."""
    if total == 0:
        return ""

    parts = []
    for sev in ["critical", "high", "medium", "low", "info"]:
        if sev in counts:
            emoji = SEVERITY_EMOJI.get(sev, "⚪")
            parts.append(f"{emoji} {counts[sev]} {sev}")

    return " | ".join(parts)


def format_findings_table(findings: list[dict], max_rows: int = 10) -> str:
    """Format top findings as a markdown table."""
    if not findings:
        return ""

    # Sort by severity (most severe first)
    sorted_findings = sorted(
        findings, key=lambda f: SEVERITY_ORDER.get(f.get("severity", "info").lower(), 4)
    )
    top = sorted_findings[:max_rows]

    lines = [
        "| Severity | File | Description |",
        "|----------|------|-------------|",
    ]
    for f in top:
        sev = f.get("severity", "info").lower()
        emoji = SEVERITY_EMOJI.get(sev, "⚪")
        file_path = f.get("file", "unknown")
        desc = f.get("message", "No description")
        # Truncate long descriptions
        if len(desc) > 80:
            desc = desc[:77] + "..."
        lines.append(f"| {emoji} {sev} | `{file_path}` | {desc} |")

    return "\n".join(lines)


def generate_comment(json_path: str, repo: str = "") -> str:
    """Generate the full PR comment markdown."""
    total, findings = load_findings(json_path)
    counts = count_by_severity(findings)

    lines = [MARKER]
    lines.append("## 🛡️ AI Code Security Reviewer — Scan Results")
    lines.append("")

    if total == 0:
        lines.append("✅ **No security findings!** Your code looks clean.")
        lines.append("")
    else:
        summary = format_summary(counts, total)
        lines.append(f"**{total} finding(s)** found: {summary}")
        lines.append("")
        lines.append("### Top Findings")
        lines.append("")
        lines.append(format_findings_table(findings))
        remaining = total - 10
        if remaining > 0:
            lines.append("")
            lines.append(f"_...and {remaining} more finding(s)._")
        lines.append("")

    # Link to Security tab
    if repo:
        lines.append(
            f"📊 [View all findings in the Security tab]"
            f"(https://github.com/{repo}/security/code-scanning)"
        )
    else:
        lines.append("📊 Check the **Security** tab for full details on all findings.")

    lines.append("")
    lines.append("---")
    lines.append("_Powered by [AI Code Security Reviewer](https://github.com/nrdiiin/ai-code-security-reviewer)_")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Format scan results as PR comment markdown")
    parser.add_argument("--input", required=True, help="Path to JSON scan results file")
    parser.add_argument("--output", required=True, help="Path to write the markdown comment")
    parser.add_argument("--repo", default="", help="GitHub repository (owner/repo) for links")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Warning: Input file {args.input} not found, creating empty comment")
        comment = f"{MARKER}\n## 🛡️ AI Code Security Reviewer — Scan Results\n\n⚠️ No scan results found.\n"
    else:
        comment = generate_comment(args.input, args.repo)

    Path(args.output).write_text(comment)
    print(f"PR comment written to {args.output}")


if __name__ == "__main__":
    main()
