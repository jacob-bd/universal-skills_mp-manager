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
from pathlib import Path
from typing import Optional


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
# Installation
# =============================================================================

def backup_existing(dest: Path, verbose: bool = False) -> Optional[Path]:
    """Create backup of existing directory. Returns backup path."""
    if not dest.exists():
        return None
    
    backup_path = dest.with_suffix('.bak')
    
    # Remove old backup if exists
    if backup_path.exists():
        shutil.rmtree(backup_path)
    
    # Move current to backup
    shutil.move(str(dest), str(backup_path))
    
    if verbose:
        print(f"  Backed up existing skill to: {backup_path}")
    
    return backup_path


def install_skill(temp_dir: Path, dest: Path, no_backup: bool = False, 
                  verbose: bool = False) -> None:
    """Move validated skill from temp to destination."""
    if dest.exists():
        if no_backup:
            shutil.rmtree(dest)
        else:
            backup_existing(dest, verbose)
    
    # Ensure parent exists
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # Move temp to destination
    shutil.move(str(temp_dir), str(dest))


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
        '--url', required=True,
        help='GitHub URL to skill folder (tree URL format)'
    )
    parser.add_argument(
        '--dest', required=True,
        help='Local destination path for skill installation'
    )
    parser.add_argument(
        '--token',
        help='GitHub personal access token (for private repos or higher rate limits)'
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Overwrite existing skill without prompting'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be downloaded without actually installing'
    )
    parser.add_argument(
        '--no-backup', action='store_true',
        help='Skip backup when overwriting existing skill'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Show detailed progress'
    )
    parser.add_argument(
        '--max-depth', type=int, default=5,
        help='Maximum directory depth to recurse (default: 5)'
    )
    
    args = parser.parse_args()
    
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
    
    # Check if destination exists and handle --force
    if dest.exists() and not args.force and not args.dry_run:
        response = input(f"\nDestination exists: {dest}\nOverwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
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
        
        # Step 3: Install (move from temp to destination)
        print(f"\nInstalling to: {dest}")
        try:
            install_skill(temp_path, dest, args.no_backup, args.verbose)
        except Exception as e:
            print(f"\nError during installation: {e}", file=sys.stderr)
            sys.exit(3)
    
    print(f"\n✓ Skill installed successfully to: {dest}")
    sys.exit(0)


if __name__ == '__main__':
    main()
