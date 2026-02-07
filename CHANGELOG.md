# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-07

### Added
- Security scanning for skill files at install time (`scan_skill.py`).
- 14 detection categories across 3 severity levels (Critical/Warning/Info).
- Detects invisible Unicode, data exfiltration URLs, shell pipe execution, credential references, command execution patterns, prompt injection, role hijacking, safety bypass attempts, HTML comments, encoded content, delimiter injection, and cross-skill escalation.
- `--skip-scan` flag for `install_skill.py` to bypass security scan.
- `docs/SECURITY_SCANNING.md` reference documentation.

## [1.0.1] - 2026-02-03

### Added
- ZIP packaging capability for claude.ai and Claude Desktop
- Hybrid API key discovery (environment variable → config file → runtime prompt)
- `config.json` template for embedded API key storage
- Documentation for claude.ai and Claude Desktop installation

### Changed
- Updated API key discovery logic to support multiple sources
- Expanded supported platforms to include claude.ai and Claude Desktop

## [1.0.0] - 2026-02-01

### Added
- Initial release of the Universal Skill Manager.
- Skill definition with `SKILL.md`.
- `install_skill.py` script for atomic, safe installation.
- Support for multiple AI ecosystems (Claude Code, Gemini, Anti-Gravity, OpenCode, etc.).
- SkillsMP.com API integration for skill discovery.
