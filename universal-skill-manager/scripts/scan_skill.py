#!/usr/bin/env python3
"""
Universal Skill Scanner

A zero-dependency security scanner for AI skill packages. Analyzes SKILL.md
files and supporting scripts for potential security risks including prompt
injection, credential exfiltration, invisible unicode, and other threats.

Usage:
    python3 scan_skill.py <path>            # Scan a skill directory or file
    python3 scan_skill.py --pretty <path>   # Pretty-print the JSON report
    python3 scan_skill.py --version         # Print version and exit

Exit codes:
    0 - Clean (no findings)
    1 - Info-level findings only
    2 - Warning-level findings present
    3 - Critical-level findings present

Output:
    JSON report to stdout with fields:
        skill_path, files_scanned, scan_timestamp,
        summary (critical, warning, info counts),
        findings (list of finding objects)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

VERSION = "1.0.0"


class Finding:
    """Represents a single security finding from the scan."""

    def __init__(self, severity, category, file, line, description, matched_text, recommendation):
        self.severity = severity
        self.category = category
        self.file = file
        self.line = line
        self.description = description
        self.matched_text = matched_text
        self.recommendation = recommendation

    def to_dict(self):
        return {
            "severity": self.severity,
            "category": self.category,
            "file": self.file,
            "line": self.line,
            "description": self.description,
            "matched_text": self.matched_text,
            "recommendation": self.recommendation,
        }


class SkillScanner:
    """Scans skill directories and files for security issues."""

    def __init__(self):
        self.findings = []
        self.files_scanned = []

    def scan_path(self, path):
        """Scan a file or directory and return a JSON-serializable report dict."""
        path = Path(path).resolve()

        if path.is_file():
            self._scan_file(path, path.parent)
        elif path.is_dir():
            for root, _dirs, files in os.walk(path):
                for fname in sorted(files):
                    file_path = Path(root) / fname
                    self._scan_file(file_path, path)
        else:
            print(f"Error: path does not exist: {path}", file=sys.stderr)
            sys.exit(1)

        return self._build_report(str(path))

    def _scan_file(self, file_path, base_path):
        """Read a file, determine its type, and call appropriate check methods."""
        file_path = Path(file_path)
        relative = str(file_path.relative_to(base_path))

        # Skip binary files and hidden files
        if file_path.name.startswith("."):
            return

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError, OSError):
            return

        self.files_scanned.append(relative)
        lines = content.splitlines()
        suffix = file_path.suffix.lower()

        # All files: invisible unicode check
        self._check_invisible_unicode(lines, relative)

        # Markdown files: all categories
        if suffix == ".md":
            self._check_all_categories(lines, relative)

        # Script files: subset of checks
        elif suffix in (".py", ".sh", ".bash"):
            self._check_exfiltration_urls(lines, relative)
            self._check_credential_references(lines, relative)
            self._check_command_execution(lines, relative)
            self._check_shell_pipe_execution(lines, relative)
            self._check_encoded_content(lines, relative)

        # Config files: subset of checks
        elif suffix in (".json", ".yaml", ".yml"):
            self._check_exfiltration_urls(lines, relative)
            self._check_credential_references(lines, relative)
            self._check_encoded_content(lines, relative)

    def _check_all_categories(self, lines, file):
        """Run all check categories against the given lines (used for .md files)."""
        self._check_exfiltration_urls(lines, file)
        self._check_shell_pipe_execution(lines, file)
        self._check_credential_references(lines, file)
        self._check_external_url_references(lines, file)
        self._check_command_execution(lines, file)
        self._check_instruction_override(lines, file)
        self._check_role_hijacking(lines, file)
        self._check_safety_bypass(lines, file)
        self._check_html_comments(lines, file)
        self._check_encoded_content(lines, file)
        self._check_prompt_extraction(lines, file)
        self._check_delimiter_injection(lines, file)
        self._check_cross_skill_escalation(lines, file)

    def _check_invisible_unicode(self, lines, file):
        """Check for invisible or zero-width unicode characters."""
        # Define all invisible/zero-width Unicode codepoint ranges
        invisible_ranges = [
            (0x200B, 0x200F),  # zero-width space, ZWNJ, ZWJ, LRM, RLM
            (0x2060, 0x2064),  # word joiner, invisible operators/separators
            (0x2066, 0x2069),  # directional isolates
            (0x202A, 0x202E),  # bidirectional overrides
            (0x206A, 0x206F),  # deprecated formatting characters
            (0xFEFF, 0xFEFF),  # byte order mark
            (0x00AD, 0x00AD),  # soft hyphen
            (0x034F, 0x034F),  # combining grapheme joiner
            (0x061C, 0x061C),  # arabic letter mark
            (0x115F, 0x1160),  # hangul filler
            (0x17B4, 0x17B5),  # khmer vowel inherent
            (0x180E, 0x180E),  # mongolian vowel separator
            (0xE0000, 0xE007F),  # unicode tag characters
        ]

        def is_invisible(ch):
            cp = ord(ch)
            for start, end in invisible_ranges:
                if start <= cp <= end:
                    return True
            return False

        for line_num, line in enumerate(lines, start=1):
            found_codepoints = set()
            for ch in line:
                if is_invisible(ch):
                    found_codepoints.add(ch)

            if found_codepoints:
                # Deduplicate and show up to 5 unique codepoints
                codepoint_strs = sorted(
                    [f"U+{ord(c):04X}" for c in found_codepoints]
                )
                shown = codepoint_strs[:5]
                suffix = f" (and {len(codepoint_strs) - 5} more)" if len(codepoint_strs) > 5 else ""
                cp_display = ", ".join(shown) + suffix

                self._add_finding(
                    severity="critical",
                    category="invisible_unicode",
                    file=file,
                    line=line_num,
                    description=f"Invisible Unicode characters detected: {cp_display}",
                    matched_text=line.strip()[:120],
                    recommendation="Remove invisible characters. These can hide malicious instructions from human review.",
                )

    def _check_exfiltration_urls(self, lines, file):
        """Check for URLs that may exfiltrate data to external servers."""
        patterns = [
            (
                r'!\[.*?\]\(https?://[^)]*[\$\{]',
                "Markdown image with variable interpolation — may exfiltrate data via URL",
            ),
            (
                r'<img\s[^>]*src\s*=\s*["\']https?://',
                "HTML img tag with external URL — may load tracking pixel or exfiltrate data",
            ),
            (
                r'!\[.*?\]\(https?://[^)]*\?[^)]*=',
                "Markdown image with query parameters — may exfiltrate data via URL parameters",
            ),
        ]

        compiled = [(re.compile(p, re.IGNORECASE), desc) for p, desc in patterns]

        for line_num, line in enumerate(lines, start=1):
            for regex, description in compiled:
                if regex.search(line):
                    self._add_finding(
                        severity="critical",
                        category="exfiltration_url",
                        file=file,
                        line=line_num,
                        description=description,
                        matched_text=line.strip()[:120],
                        recommendation="Remove or replace with a local/trusted image. External images in skill files can leak sensitive data.",
                    )
                    break  # One finding per line

    def _check_shell_pipe_execution(self, lines, file):
        """Check for shell commands piped from remote sources."""
        pattern = re.compile(
            r'(curl|wget)\s+[^|]*\|\s*(bash|sh|zsh|python[23]?|perl|ruby|node)',
            re.IGNORECASE,
        )

        for line_num, line in enumerate(lines, start=1):
            match = pattern.search(line)
            if match:
                self._add_finding(
                    severity="critical",
                    category="shell_pipe_execution",
                    file=file,
                    line=line_num,
                    description="Remote content piped directly into shell interpreter — arbitrary code execution risk",
                    matched_text=line.strip()[:120],
                    recommendation="Download the script first, review it, then execute. Never pipe remote content directly into a shell.",
                )

    def _check_credential_references(self, lines, file):
        """Check for references to credentials, tokens, or API keys."""
        path_patterns = [
            r'~/\.ssh/',
            r'~/\.aws/',
            r'~/\.gnupg/',
            r'~/\.env\b',
            r'\.credentials',
            r'id_rsa',
            r'id_ed25519',
            r'id_ecdsa',
            r'\.pem\b',
            r'\.key\b',
            r'/etc/passwd',
            r'/etc/shadow',
        ]
        env_patterns = [
            r'\$\{?GITHUB_TOKEN\}?',
            r'\$\{?OPENAI_API_KEY\}?',
            r'\$\{?ANTHROPIC_API_KEY\}?',
            r'\$\{?AWS_SECRET_ACCESS_KEY\}?',
            r'\$\{?AWS_ACCESS_KEY_ID\}?',
            r'\$\{?DATABASE_URL\}?',
            r'\$\{?DB_PASSWORD\}?',
            r'\$\{?SECRET_KEY\}?',
            r'\$\{?PRIVATE_KEY\}?',
            r'\$\{?API_SECRET\}?',
            r'\$\{?GOOGLE_API_KEY\}?',
            r'\$\{?STRIPE_SECRET\}?',
        ]

        compiled_path = [re.compile(p, re.IGNORECASE) for p in path_patterns]
        compiled_env = [re.compile(p, re.IGNORECASE) for p in env_patterns]

        for line_num, line in enumerate(lines, start=1):
            for regex in compiled_path:
                if regex.search(line):
                    self._add_finding(
                        severity="warning",
                        category="credential_reference",
                        file=file,
                        line=line_num,
                        description="Reference to credential or sensitive file path detected",
                        matched_text=line.strip()[:100],
                        recommendation="Avoid referencing credential files directly. Use environment variables or secure vaults instead.",
                    )
                    break
            else:
                for regex in compiled_env:
                    if regex.search(line):
                        self._add_finding(
                            severity="warning",
                            category="credential_reference",
                            file=file,
                            line=line_num,
                            description="Reference to sensitive environment variable or API key detected",
                            matched_text=line.strip()[:100],
                            recommendation="Avoid hardcoding or directly referencing sensitive environment variables in skill files.",
                        )
                        break

    def _check_external_url_references(self, lines, file):
        """Check for external URL references that may fetch untrusted content."""
        patterns = [
            r'\bcurl\s+.*https?://',
            r'\bwget\s+.*https?://',
            r'\bfetch\s*\(\s*["\']https?://',
            r'\brequests?\.(get|post|put|delete)\s*\(',
            r'\bhttp\.(get|post|put|delete)\s*\(',
            r'\burllib\.request',
        ]

        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

        for line_num, line in enumerate(lines, start=1):
            for regex in compiled:
                if regex.search(line):
                    self._add_finding(
                        severity="warning",
                        category="external_url",
                        file=file,
                        line=line_num,
                        description="External URL reference detected — may fetch untrusted content",
                        matched_text=line.strip()[:100],
                        recommendation="Verify the URL points to a trusted source. Avoid fetching arbitrary remote content in skill files.",
                    )
                    break

    def _check_command_execution(self, lines, file):
        """Check for dangerous command execution patterns."""
        patterns = [
            r'\beval\s*\(',
            r'\bexec\s*\(',
            r'\bos\.system\s*\(',
            r'\bsubprocess\.(run|call|Popen|check_output)\s*\(',
            r'\bsh\s+-c\s+',
            r'\bbash\s+-c\s+',
            r'\bRuntime\.exec\s*\(',
            r'\bos\.popen\s*\(',
            r'\bcommands\.getoutput\s*\(',
        ]

        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

        for line_num, line in enumerate(lines, start=1):
            for regex in compiled:
                if regex.search(line):
                    self._add_finding(
                        severity="warning",
                        category="command_execution",
                        file=file,
                        line=line_num,
                        description="Dangerous command execution pattern detected",
                        matched_text=line.strip()[:100],
                        recommendation="Avoid using dynamic command execution. Use safer alternatives or validate all inputs.",
                    )
                    break

    def _check_instruction_override(self, lines, file):
        """Check for attempts to override system instructions."""
        patterns = [
            r'ignore\s+(all\s+)?previous\s+instructions?',
            r'disregard\s+(all\s+)?(previous\s+|prior\s+)?instructions?',
            r'disregard\s+(all\s+)?(previous\s+|prior\s+)?directives?',
            r'forget\s+(all\s+)?(previous\s+|everything\s+)',
            r'new\s+instructions?\s+(follow|are|:)',
            r'override\s+(all\s+)?previous\s+instructions?',
            r'cancel\s+(all\s+)?prior\s+instructions?',
            r'your\s+(new|updated)\s+instructions?\s+(are|:)',
            r'do\s+not\s+follow\s+(your\s+)?(original|previous)',
        ]

        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

        for line_num, line in enumerate(lines, start=1):
            for regex in compiled:
                if regex.search(line):
                    self._add_finding(
                        severity="warning",
                        category="instruction_override",
                        file=file,
                        line=line_num,
                        description="Potential instruction override attempt detected",
                        matched_text=line.strip()[:100],
                        recommendation="Skill files should not attempt to override or cancel prior instructions. This is a prompt injection indicator.",
                    )
                    break

    def _check_role_hijacking(self, lines, file):
        """Check for role/persona hijacking attempts."""
        patterns = [
            r'you\s+are\s+now\s+(?!going|ready|able)',
            r'act\s+as\s+(if\s+)?(you\s+are|an?\s+)',
            r'pretend\s+(to\s+be|you\s+are)',
            r'assume\s+the\s+role\s+of',
            r'enter\s+developer\s+mode',
            r'\bDAN\s+mode\b',
            r'unrestricted\s+mode',
            r'you\s+have\s+no\s+restrictions',
            r'enable\s+jailbreak',
            r'you\s+are\s+no\s+longer\s+bound',
        ]

        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

        for line_num, line in enumerate(lines, start=1):
            for regex in compiled:
                if regex.search(line):
                    self._add_finding(
                        severity="warning",
                        category="role_hijacking",
                        file=file,
                        line=line_num,
                        description="Potential role/persona hijacking attempt detected",
                        matched_text=line.strip()[:100],
                        recommendation="Skill files should not attempt to change the AI's role or persona. This is a prompt injection indicator.",
                    )
                    break

    def _check_safety_bypass(self, lines, file):
        """Check for attempts to bypass safety measures."""
        patterns = [
            r'bypass\s+(safety|security|filter|restriction)',
            r'disable\s+(content\s+)?filter',
            r'remove\s+(all\s+)?restrictions?',
            r'ignore\s+safety\s+protocols?',
            r'without\s+(any\s+)?restrictions?',
            r'system\s+override',
            r'no\s+ethical\s+guidelines',
            r'disregard\s+(any\s+)?filters?',
            r'turn\s+off\s+(safety|content\s+filter)',
        ]

        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

        for line_num, line in enumerate(lines, start=1):
            for regex in compiled:
                if regex.search(line):
                    self._add_finding(
                        severity="warning",
                        category="safety_bypass",
                        file=file,
                        line=line_num,
                        description="Potential safety bypass attempt detected",
                        matched_text=line.strip()[:100],
                        recommendation="Skill files should not attempt to bypass safety measures. This is a prompt injection indicator.",
                    )
                    break

    def _check_html_comments(self, lines, file):
        """Check for hidden instructions in HTML comments."""
        # Only check .md files
        if not file.endswith(".md"):
            return

        in_comment = False
        comment_start_line = 0
        comment_content = ""

        for line_num, line in enumerate(lines, start=1):
            if not in_comment:
                # Check for comment opening
                start_idx = line.find("<!--")
                if start_idx == -1:
                    continue

                # Check if comment closes on the same line
                end_idx = line.find("-->", start_idx + 4)
                if end_idx != -1:
                    # Single-line comment
                    content = line[start_idx + 4:end_idx].strip()
                    display = content[:80] if len(content) > 80 else content
                    self._add_finding(
                        severity="warning",
                        category="html_comment",
                        file=file,
                        line=line_num,
                        description=f"HTML comment detected — may contain hidden instructions: {display}",
                        matched_text=line.strip()[:100],
                        recommendation="Review HTML comments carefully. They are invisible in rendered markdown and can hide malicious instructions.",
                    )
                else:
                    # Multi-line comment starts
                    in_comment = True
                    comment_start_line = line_num
                    comment_content = line[start_idx + 4:]
            else:
                # Inside a multi-line comment, look for closing
                end_idx = line.find("-->")
                if end_idx != -1:
                    # Comment closes on this line
                    comment_content += "\n" + line[:end_idx]
                    content = comment_content.strip()
                    display = content[:80] if len(content) > 80 else content
                    self._add_finding(
                        severity="warning",
                        category="html_comment",
                        file=file,
                        line=comment_start_line,
                        description=f"HTML comment detected — may contain hidden instructions: {display}",
                        matched_text=comment_content.strip()[:100],
                        recommendation="Review HTML comments carefully. They are invisible in rendered markdown and can hide malicious instructions.",
                    )
                    in_comment = False
                    comment_content = ""
                else:
                    comment_content += "\n" + line

    def _check_encoded_content(self, lines, file):
        """Check for base64 or other encoded content that may hide payloads."""
        patterns = [
            (re.compile(r'[A-Za-z0-9+/]{40,}={0,2}'), "Long base64-encoded string detected"),
            (re.compile(r'(?:\\x[0-9a-fA-F]{2}){4,}'), "Hex escape sequences detected"),
            (re.compile(r'(?:\\u[0-9a-fA-F]{4}){3,}'), "Unicode escape sequences detected"),
            (re.compile(r'(?:&#x?[0-9a-fA-F]+;){3,}'), "HTML entity sequences detected"),
            (re.compile(r'(?:%[0-9a-fA-F]{2}){6,}'), "URL-encoded sequences detected"),
        ]

        for line_num, line in enumerate(lines, start=1):
            for regex, description in patterns:
                match = regex.search(line)
                if match:
                    matched = match.group()
                    length = len(matched)
                    display = (matched[:60] + "...") if len(matched) > 60 else matched
                    self._add_finding(
                        severity="info",
                        category="encoded_content",
                        file=file,
                        line=line_num,
                        description=f"{description} ({length} chars)",
                        matched_text=display,
                        recommendation="Review encoded content carefully. Encoded strings can hide malicious payloads from human review.",
                    )
                    break  # One finding per line

    def _check_prompt_extraction(self, lines, file):
        """Check for attempts to extract system prompts or instructions."""
        patterns = [
            r'reveal\s+(your\s+)?system\s+prompt',
            r'show\s+(me\s+)?your\s+instructions',
            r'print\s+(your\s+)?(initial\s+)?prompt',
            r'output\s+your\s+(configuration|instructions)',
            r'what\s+(were\s+you|are\s+your)\s+(told|instructions)',
            r'repeat\s+the\s+(above|previous)\s+text',
            r'display\s+(your\s+)?(system\s+)?(prompt|instructions)',
        ]

        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

        for line_num, line in enumerate(lines, start=1):
            for regex in compiled:
                if regex.search(line):
                    self._add_finding(
                        severity="info",
                        category="prompt_extraction",
                        file=file,
                        line=line_num,
                        description="Potential prompt extraction attempt detected",
                        matched_text=line.strip()[:100],
                        recommendation="Skill files should not attempt to extract system prompts or instructions from the AI.",
                    )
                    break  # One finding per line

    def _check_delimiter_injection(self, lines, file):
        """Check for delimiter injection attacks."""
        # Case-sensitive exact token patterns
        tokens = [
            r'<\|system\|>',
            r'<\|user\|>',
            r'<\|assistant\|>',
            r'<\|im_start\|>',
            r'<\|im_end\|>',
            r'\[INST\]',
            r'\[/INST\]',
            r'<<SYS>>',
            r'<</SYS>>',
        ]

        compiled = [re.compile(p) for p in tokens]

        for line_num, line in enumerate(lines, start=1):
            for regex in compiled:
                match = regex.search(line)
                if match:
                    self._add_finding(
                        severity="info",
                        category="delimiter_injection",
                        file=file,
                        line=line_num,
                        description=f"LLM delimiter token detected: {match.group()}",
                        matched_text=line.strip()[:100],
                        recommendation="Skill files should not contain LLM chat delimiters. These can be used to inject system-level instructions.",
                    )
                    break  # One finding per line

    def _check_cross_skill_escalation(self, lines, file):
        """Check for attempts to escalate privileges across skills."""
        patterns = [
            r'install\s+(this\s+|the\s+)?skill\s+from\s+https?://',
            r'download\s+(this\s+|the\s+)?skill\s+from',
            r'fetch\s+(this\s+|the\s+)?(skill|extension)\s+from',
            r'add\s+(this\s+)?to\s+~/\.(claude|gemini|cursor|codex|roo)',
            r'cp\s+.*\s+~/\.(claude|gemini|cursor|codex|roo)/(skills|extensions)',
            r'git\s+clone\s+.*\s+~/\.(claude|gemini|cursor|codex)',
        ]

        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

        for line_num, line in enumerate(lines, start=1):
            for regex in compiled:
                if regex.search(line):
                    self._add_finding(
                        severity="info",
                        category="cross_skill_escalation",
                        file=file,
                        line=line_num,
                        description="Potential cross-skill escalation attempt detected",
                        matched_text=line.strip()[:100],
                        recommendation="Skill files should not attempt to install other skills or modify AI tool directories. Use the skill manager for installations.",
                    )
                    break  # One finding per line

    def _add_finding(self, severity, category, file, line, description, matched_text, recommendation):
        """Add a finding to the findings list."""
        finding = Finding(
            severity=severity,
            category=category,
            file=file,
            line=line,
            description=description,
            matched_text=matched_text,
            recommendation=recommendation,
        )
        self.findings.append(finding)

    def _build_report(self, skill_path):
        """Build and return the JSON report dict."""
        critical_count = sum(1 for f in self.findings if f.severity == "critical")
        warning_count = sum(1 for f in self.findings if f.severity == "warning")
        info_count = sum(1 for f in self.findings if f.severity == "info")

        return {
            "skill_path": skill_path,
            "files_scanned": list(self.files_scanned),
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "critical": critical_count,
                "warning": warning_count,
                "info": info_count,
            },
            "findings": [f.to_dict() for f in self.findings],
        }


def exit_code_from_report(report):
    """Determine the exit code based on the report summary."""
    summary = report["summary"]
    if summary["critical"] > 0:
        return 3
    if summary["warning"] > 0:
        return 2
    if summary["info"] > 0:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Scan AI skill packages for security issues."
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to a skill directory or file to scan",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output with indentation",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit",
    )

    args = parser.parse_args()

    if args.version:
        print(f"scan_skill.py {VERSION}")
        sys.exit(0)

    if not args.path:
        parser.error("the following arguments are required: path")

    scanner = SkillScanner()
    report = scanner.scan_path(args.path)

    indent = 2 if args.pretty else None
    print(json.dumps(report, indent=indent))

    sys.exit(exit_code_from_report(report))


if __name__ == "__main__":
    main()
