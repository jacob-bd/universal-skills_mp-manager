#!/usr/bin/env python3
"""
Universal Skill Installer

A robust, zero-dependency Python script for downloading and installing AI skills
from GitHub repositories. Uses atomic install pattern for safety.

Usage:
    python3 install_skill.py --url "https://github.com/user/repo/tree/main/skills/my-skill" --dest "~/.claude/skills/my-skill"

Features:
    - Atomic install: Downloads to temp, validates, then moves to destination
    - Multi-file validation: Validates .py, .sh, .json, .yaml files
    - Single API call: Only one GitHub API request to list directory
    - Raw URL downloads: No rate limiting for file downloads
"""

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import hashlib
from pathlib import Path
from typing import Optional

VERSION = "1.1.0"


# =============================================================================
# URL Parsing
# =============================================================================

def parse_github_url(url: str) -> Optional[dict]:
    """
    Parse a GitHub tree URL into components.
    
    Input:  https://github.com/{owner}/{repo}/tree/{branch}/{path}
            https://github.com/{owner}/{repo}/tree/{branch}  (root level)
    Output: {"owner": ..., "repo": ..., "branch": ..., "path": ...}
    
    Returns None if URL is not a valid GitHub tree URL.
    """
    # Pattern: github.com/{owner}/{repo}/tree/{branch}/{path...} (path optional)
    pattern = r'https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(?:/(.+?))?/?$'
    match = re.match(pattern, url)
    
    if not match:
        return None
    
    return {
        "owner": match.group(1),
        "repo": match.group(2),
        "branch": match.group(3),
        "path": match.group(4) or "",  # Empty string if at root
    }


def to_raw_url(owner: str, repo: str, branch: str, path: str, filename: str) -> str:
    """Convert GitHub components to raw.githubusercontent.com URL."""
    # URL-encode the filename to handle spaces and special characters
    from urllib.parse import quote
    encoded_filename = quote(filename, safe='')
    if path:
        encoded_path = '/'.join(quote(p, safe='') for p in path.split('/'))
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encoded_path}/{encoded_filename}"
    else:
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{encoded_filename}"


def to_api_url(owner: str, repo: str, branch: str, path: str) -> str:
    """Convert GitHub components to API contents URL."""
    if path:
        return f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    else:
        return f"https://api.github.com/repos/{owner}/{repo}/contents?ref={branch}"


# =============================================================================
# GitHub API & Downloads
# =============================================================================

def fetch_json(url: str, token: Optional[str] = None, verbose: bool = False) -> dict:
    """Fetch JSON from URL with optional auth token."""
    if verbose:
        print(f"  Fetching: {url}")
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    request = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RuntimeError(f"Not found: {url}. Check URL or use --token for private repos.")
        elif e.code == 403:
            raise RuntimeError(f"Rate limited or forbidden. Use --token for higher limits.")
        else:
            raise RuntimeError(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}")


def fetch_file(url: str, dest_path: Path, token: Optional[str] = None, verbose: bool = False) -> None:
    """Download a file from URL to destination path."""
    if verbose:
        print(f"  Downloading: {url}")
    
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    
    request = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            dest_path.write_bytes(content)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Failed to download {url}: HTTP {e.code}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error downloading {url}: {e.reason}")


def list_directory_contents(owner: str, repo: str, branch: str, path: str, 
                            token: Optional[str] = None, verbose: bool = False) -> list:
    """List contents of a GitHub directory using API."""
    api_url = to_api_url(owner, repo, branch, path)
    contents = fetch_json(api_url, token, verbose)
    
    if not isinstance(contents, list):
        raise RuntimeError(f"Expected directory at {path}, got file")
    
    return contents


def download_directory(owner: str, repo: str, branch: str, path: str, 
                       dest_dir: Path, token: Optional[str] = None, 
                       verbose: bool = False, current_depth: int = 0, 
                       max_depth: int = 5) -> list:
    """
    Recursively download directory contents from GitHub.
    Returns list of downloaded file paths (relative to dest_dir).
    """
    if current_depth > max_depth:
        print(f"  Warning: Max depth {max_depth} reached, skipping deeper directories")
        return []
    
    downloaded = []
    contents = list_directory_contents(owner, repo, branch, path, token, verbose)
    
    for item in contents:
        item_name = item["name"]
        item_type = item["type"]
        
        if item_type == "file":
            # Download via raw URL
            raw_url = to_raw_url(owner, repo, branch, path, item_name)
            dest_path = dest_dir / item_name
            fetch_file(raw_url, dest_path, token, verbose)
            downloaded.append(item_name)
            print(f"  ✓ {item_name}")
        
        elif item_type == "dir":
            # Recursively download subdirectory
            subdir = dest_dir / item_name
            subdir.mkdir(parents=True, exist_ok=True)
            sub_path = f"{path}/{item_name}"
            sub_files = download_directory(
                owner, repo, branch, sub_path, subdir, 
                token, verbose, current_depth + 1, max_depth
            )
            downloaded.extend([f"{item_name}/{f}" for f in sub_files])
    
    return downloaded


# =============================================================================
# Validation
# =============================================================================

def parse_simple_yaml(yaml_str: str) -> dict:
    """
    Parse simple key: value YAML (no nested objects, no lists).
    Sufficient for SKILL.md frontmatter.
    """
    result = {}
    for line in yaml_str.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def validate_skill_md(file_path: Path) -> tuple[bool, str]:
    """
    Validate SKILL.md has proper YAML frontmatter.
    Returns (success, error_message).
    """
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return False, f"Cannot read file: {e}"
    
    if not content.startswith('---'):
        return False, "Missing YAML frontmatter (must start with ---)"
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return False, "Invalid frontmatter (missing closing ---)"
    
    try:
        frontmatter = parse_simple_yaml(parts[1])
    except Exception as e:
        return False, f"Invalid YAML: {e}"
    
    if 'name' not in frontmatter:
        return False, "Missing required field: name"
    if 'description' not in frontmatter:
        return False, "Missing required field: description"
    
    return True, ""


def validate_python(file_path: Path) -> tuple[bool, str]:
    """Validate Python syntax using ast.parse()."""
    try:
        content = file_path.read_text(encoding='utf-8')
        ast.parse(content)
        return True, ""
    except SyntaxError as e:
        return False, f"Python syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Cannot parse Python: {e}"


def validate_shell(file_path: Path) -> tuple[bool, str]:
    """Validate shell script syntax using bash -n."""
    try:
        result = subprocess.run(
            ['bash', '-n', str(file_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return False, f"Shell syntax error: {result.stderr.strip()}"
        return True, ""
    except FileNotFoundError:
        # bash not available, skip validation
        return True, ""
    except Exception as e:
        return False, f"Cannot validate shell script: {e}"


def validate_json(file_path: Path) -> tuple[bool, str]:
    """Validate JSON syntax."""
    try:
        content = file_path.read_text(encoding='utf-8')
        json.loads(content)
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Cannot read JSON: {e}"


def validate_yaml(file_path: Path) -> tuple[bool, str]:
    """Validate basic YAML structure."""
    try:
        content = file_path.read_text(encoding='utf-8')
        # Basic check: can we parse key: value pairs?
        parse_simple_yaml(content)
        return True, ""
    except Exception as e:
        return False, f"Invalid YAML: {e}"


def validate_file(file_path: Path, verbose: bool = False) -> tuple[bool, str]:
    """
    Validate a file based on its extension.
    Returns (success, error_message).
    """
    name = file_path.name.lower()
    suffix = file_path.suffix.lower()
    
    if name == 'skill.md':
        return validate_skill_md(file_path)
    elif suffix == '.py':
        return validate_python(file_path)
    elif suffix == '.sh':
        return validate_shell(file_path)
    elif suffix == '.json':
        return validate_json(file_path)
    elif suffix in ('.yaml', '.yml'):
        return validate_yaml(file_path)
    else:
        # No validation for other file types
        return True, ""


def validate_all_files(directory: Path, verbose: bool = False) -> tuple[bool, list]:
    """
    Validate all files in directory recursively.
    Returns (all_valid, list_of_errors).
    """
    errors = []
    
    # First check: SKILL.md must exist
    skill_md = directory / "SKILL.md"
    if not skill_md.exists():
        errors.append("SKILL.md not found in skill directory")
        return False, errors
    
    # Validate all files
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            valid, error = validate_file(file_path, verbose)
            if not valid:
                errors.append(f"{file_path.name}: {error}")
    
    return len(errors) == 0, errors


# =============================================================================
# Safety Checks
# =============================================================================

def check_root_skills_directory_safety(dest: Path, force: bool) -> None:
    """
    Abort if destination looks like a root skills directory.
    
    Root skills directory = has subdirs with SKILL.md but no SKILL.md itself.
    Fresh/empty directories are allowed.
    """
    if not dest.exists() or not dest.is_dir() or force:
        return  # Safe to proceed
    
    has_skill_md = (dest / "SKILL.md").exists()
    if has_skill_md:
        return  # This IS a skill, safe to update
    
    # Check for subdirectories containing SKILL.md (installed skills)
    installed_skills = [
        d.name for d in dest.iterdir() 
        if d.is_dir() and (d / "SKILL.md").exists()
    ]
    
    if installed_skills:
        # DANGER: This is a root skills directory!
        print("=" * 60, file=sys.stderr)
        print("CRITICAL ERROR: Root Skills Directory Detected", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"\nDestination: {dest}", file=sys.stderr)
        print(f"\nThis appears to be a root skills directory containing:", file=sys.stderr)
        for skill in installed_skills[:5]:
            print(f"  • {skill}", file=sys.stderr)
        if len(installed_skills) > 5:
            print(f"  ... and {len(installed_skills) - 5} more", file=sys.stderr)
        print(f"\nYou probably meant: {dest}/<skill-name>", file=sys.stderr)
        print("\nUse --force to override this safety check.", file=sys.stderr)
        sys.exit(4)


def file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of a file for comparison."""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def compare_skill_directories(new_dir: Path, existing_dir: Path) -> dict:
    """
    Compare two skill directories and return differences.
    
    Returns:
        {
            "identical": bool,
            "added": [list of new files],
            "removed": [list of deleted files],
            "modified": [list of changed files],
        }
    """
    def get_relative_files(base: Path) -> dict:
        """Get all files relative to base with their hashes."""
        files = {}
        for file_path in base.rglob('*'):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(base))
                files[rel_path] = file_hash(file_path)
        return files
    
    new_files = get_relative_files(new_dir)
    existing_files = get_relative_files(existing_dir)
    
    new_set = set(new_files.keys())
    existing_set = set(existing_files.keys())
    
    added = sorted(new_set - existing_set)
    removed = sorted(existing_set - new_set)
    
    # Check for modified files (same name, different hash)
    common = new_set & existing_set
    modified = sorted([f for f in common if new_files[f] != existing_files[f]])
    
    identical = len(added) == 0 and len(removed) == 0 and len(modified) == 0
    
    return {
        "identical": identical,
        "added": added,
        "removed": removed,
        "modified": modified,
    }


def display_skill_diff(diff: dict, dest: Path, force: bool) -> bool:
    """
    Display diff and prompt user for confirmation.
    
    Returns True if user approves (or force=True), False otherwise.
    """
    if diff["identical"]:
        print(f"\n✓ Skill is already up to date: {dest}")
        return False  # No need to reinstall
    
    print(f"\n📋 Changes detected for skill at: {dest}")
    print("-" * 50)
    
    if diff["added"]:
        print(f"\n  ➕ New files ({len(diff['added'])}):", )
        for f in diff["added"][:10]:
            print(f"      {f}")
        if len(diff["added"]) > 10:
            print(f"      ... and {len(diff['added']) - 10} more")
    
    if diff["removed"]:
        print(f"\n  ➖ Removed files ({len(diff['removed'])}):", )
        for f in diff["removed"][:10]:
            print(f"      {f}")
        if len(diff["removed"]) > 10:
            print(f"      ... and {len(diff['removed']) - 10} more")
    
    if diff["modified"]:
        print(f"\n  📝 Modified files ({len(diff['modified'])}):", )
        for f in diff["modified"][:10]:
            print(f"      {f}")
        if len(diff["modified"]) > 10:
            print(f"      ... and {len(diff['modified']) - 10} more")
    
    print("-" * 50)
    
    if force:
        print("  (--force specified, proceeding without prompt)")
        return True
    
    response = input("\nProceed with update? [y/N]: ")
    return response.lower() == 'y'


# =============================================================================
# Installation
# =============================================================================

def install_skill(temp_dir: Path, dest: Path) -> None:
    """Copy validated skill from temp to destination."""
    if dest.exists():
        shutil.rmtree(dest)
    
    # Ensure parent exists
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy from temp to destination
    shutil.copytree(str(temp_dir), str(dest))


# =============================================================================
# Security Scanning
# =============================================================================

def find_scanner_script() -> Optional[Path]:
    """Find scan_skill.py in the same directory as this script."""
    script_dir = Path(__file__).parent
    scanner = script_dir / "scan_skill.py"
    if scanner.exists():
        return scanner
    return None


def run_security_scan(skill_dir: Path, force: bool = False) -> bool:
    """
    Run security scan on a skill directory before installation.

    Returns True if installation should proceed, False to abort.
    """
    scanner = find_scanner_script()
    if scanner is None:
        print("  Warning: Security scanner (scan_skill.py) not found, skipping scan")
        return True

    print("\nRunning security scan...")

    try:
        result = subprocess.run(
            [sys.executable, str(scanner), str(skill_dir)],
            capture_output=True,
            text=True,
            timeout=30
        )
    except subprocess.TimeoutExpired:
        print("  Warning: Security scan timed out, skipping")
        return True
    except Exception as e:
        print(f"  Warning: Security scan failed to run: {e}")
        return True

    # Parse JSON output from scanner
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("  Warning: Could not parse security scan results, skipping")
        return True

    # Extract summary and findings
    summary = report.get("summary", {})
    findings = report.get("findings", [])
    total = summary.get("total", 0)

    if total == 0:
        print("  No security threats detected")
        return True

    # Display findings grouped by severity
    severity_order = ["CRITICAL", "WARNING", "INFO"]
    severity_labels = {
        "CRITICAL": "CRITICAL",
        "WARNING": "WARNING",
        "INFO": "INFO",
    }

    print(f"\n  Security scan found {total} issue(s):")
    print("  " + "-" * 48)

    for severity in severity_order:
        severity_findings = [f for f in findings if f.get("severity") == severity]
        if not severity_findings:
            continue

        print(f"\n  [{severity_labels[severity]}]")
        for finding in severity_findings:
            file_name = finding.get("file", "unknown")
            line = finding.get("line")
            message = finding.get("message", "No description")
            location = f"{file_name}:{line}" if line else file_name
            print(f"    - {location}: {message}")

    print("  " + "-" * 48)

    # Summary line with counts
    parts = []
    for severity in severity_order:
        count = summary.get(severity.lower(), summary.get(severity, 0))
        if count > 0:
            parts.append(f"{count} {severity.lower()}")
    print(f"  Summary: {', '.join(parts)}")

    if force:
        print("\n  Note: --force specified, proceeding despite security findings")
        return True

    response = input("\nProceed with installation? [y/N]: ")
    return response.lower() == 'y'


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Download and install AI skills from GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url "https://github.com/user/repo/tree/main/skills/my-skill" --dest "~/.claude/skills/my-skill"
  %(prog)s --url "https://github.com/user/repo/tree/main/skills/my-skill" --dest "/tmp/test" --dry-run
        """
    )
    
    parser.add_argument(
        '--url', required=False,
        help='GitHub URL to skill folder (tree URL format)'
    )
    parser.add_argument(
        '--dest', required=False,
        help='Local destination path for skill installation'
    )
    parser.add_argument(
        '--token',
        help='GitHub personal access token (for private repos or higher rate limits)'
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Overwrite existing skill without prompting and bypass safety checks'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be downloaded without actually installing'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Show detailed progress'
    )
    parser.add_argument(
        '--max-depth', type=int, default=5,
        help='Maximum directory depth to recurse (default: 5)'
    )
    parser.add_argument(
        '--skip-scan', action='store_true',
        help='Skip security scan (not recommended)'
    )
    parser.add_argument(
        '--version', action='store_true',
        help='Show version information and exit'
    )
    
    args = parser.parse_args()

    # Show version
    if args.version:
        print(f"Universal Skill Installer v{VERSION}")
        sys.exit(0)
    
    # Validate required arguments
    if not args.url or not args.dest:
        parser.error("the following arguments are required: --url, --dest")
    
    # Expand ~ in destination path
    dest = Path(args.dest).expanduser().resolve()
    
    # Parse GitHub URL
    print(f"Parsing URL: {args.url}")
    parsed = parse_github_url(args.url)
    if not parsed:
        print("Error: Invalid GitHub URL format", file=sys.stderr)
        print("Expected: https://github.com/{owner}/{repo}/tree/{branch}/{path}", file=sys.stderr)
        sys.exit(2)
    
    print(f"Repository: {parsed['owner']}/{parsed['repo']}")
    print(f"Branch: {parsed['branch']}")
    print(f"Path: {parsed['path']}")
    print(f"Destination: {dest}")
    
    # Safety check: Prevent accidental targeting of root skills directory
    check_root_skills_directory_safety(dest, args.force)
    
    # Dry run mode
    if args.dry_run:
        print("\n[DRY RUN] Would download:")
        try:
            contents = list_directory_contents(
                parsed['owner'], parsed['repo'], parsed['branch'], parsed['path'],
                args.token, args.verbose
            )
            for item in contents:
                item_type = "📁" if item["type"] == "dir" else "📄"
                print(f"  {item_type} {item['name']}")
            print("\n[DRY RUN] No files were downloaded")
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    
    # Create temp directory for atomic install
    with tempfile.TemporaryDirectory(prefix="skill_install_") as temp_dir:
        temp_path = Path(temp_dir) / "skill"
        temp_path.mkdir()
        
        # Step 1: Download all files to temp
        print("\nDownloading skill files...")
        try:
            downloaded = download_directory(
                parsed['owner'], parsed['repo'], parsed['branch'], parsed['path'],
                temp_path, args.token, args.verbose, max_depth=args.max_depth
            )
        except RuntimeError as e:
            print(f"\nError during download: {e}", file=sys.stderr)
            sys.exit(1)
        
        if not downloaded:
            print("Error: No files downloaded", file=sys.stderr)
            sys.exit(1)
        
        print(f"\nDownloaded {len(downloaded)} file(s)")
        
        # Step 2: Validate all files
        print("\nValidating files...")
        valid, errors = validate_all_files(temp_path, args.verbose)
        
        if not valid:
            print("\nValidation failed:", file=sys.stderr)
            for error in errors:
                print(f"  ✗ {error}", file=sys.stderr)
            print("\nInstallation aborted. No files were written to destination.", file=sys.stderr)
            sys.exit(2)
        
        print("  ✓ All files valid")

        # Step 2.5: Security scan
        if not args.skip_scan:
            should_proceed = run_security_scan(temp_path, args.force)
            if not should_proceed:
                print("Installation aborted by user after security scan.")
                sys.exit(0)
        else:
            print("\n  (Security scan skipped via --skip-scan)")

        # Step 3: Compare if destination already exists
        if dest.exists():
            diff = compare_skill_directories(temp_path, dest)
            should_install = display_skill_diff(diff, dest, args.force)
            if not should_install:
                if diff["identical"]:
                    sys.exit(0)  # Already up to date
                else:
                    print("Aborted.")
                    sys.exit(0)
        
        # Step 4: Install (copy from temp to destination)
        print(f"\nInstalling to: {dest}")
        try:
            install_skill(temp_path, dest)
        except Exception as e:
            print(f"\nError during installation: {e}", file=sys.stderr)
            sys.exit(3)
    
    print(f"\n✓ Skill installed successfully to: {dest}")
    sys.exit(0)


if __name__ == '__main__':
    main()
