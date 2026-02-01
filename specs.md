# Specification: Universal Skill Downloader (`scripts/install_skill.py`)

## 1. Objective
Create a robust, standalone Python script to download a specific directory (skill) from a GitHub repository without cloning the entire history. This script replaces the fragile "curl/manual" logic currently relied upon by the LLM.

## 2. Technical Constraints
- **Language:** Python 3.
- **Dependencies:** Standard Library ONLY (`urllib`, `json`, `argparse`, `pathlib`). No `pip install` required to ensure it runs immediately on any environment.
- **Platform:** Cross-platform (macOS/Linux/Windows).

## 3. Core Logic
The script must function as follows:

```bash
python3 install_skill.py --url "https://github.com/user/repo/tree/main/skills/my-skill" --dest "~/.claude/skills/my-skill"
```

### 3.1. URL Parsing
It must accurately parse standard GitHub tree URLs to extract:
- Owner
- Repo
- Branch (default to `HEAD` if not found, but tree URLs usually have it)
- Path

### 3.2. Fetching Strategy (The "Contents API" Method)
Instead of `git clone`, use the GitHub REST API to list directory contents:
`GET https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}`

- **Iterate:** Loop through the JSON response.
- **Files:** Download content using the `download_url` (raw.githubusercontent.com) field.
- **Directories:** Recursively fetch sub-directories (skills may have `references/` or `scripts/` folders).
- **Rate Limits:** Handle 403/429 errors gracefully (tell user if token is needed).

### 3.3. Writing to Disk
- Create the destination directory if it doesn't exist.
- Overwrite existing files (or prompt? Default to overwrite for automation).
- Maintain executable permissions for scripts (`.sh`, `.py`).

## 4. Input Arguments

| Argument | Flag | Required | Description |
| :--- | :--- | :--- | :--- |
| **GitHub URL** | `--url` | Yes | Full URL to the skill folder on GitHub. |
| **Destination** | `--dest` | Yes | Local path where the skill should be installed. |
| **Token** | `--token` | No | GitHub PAT for private repos or higher rate limits. |
| **Force** | `--force` | No | Overwrite without asking (for non-interactive mode). |

## 5. Output / Interface
- **Stdout:** Progress logs ("Downloading SKILL.md...", "Installed to /path/to/skill").
- **Exit Code:**
    - `0`: Success
    - `1`: Network/API Error
    - `2`: Invalid URL/Input

## 6. Sync Logic (Agent Integration)
The Universal Skill Manager (Agent) will rely on this script.
*   **Agent Responsibility:** Discover the URL, determine the target paths (Claude, Gemini, etc.).
*   **Script Responsibility:** Reliable transport of bytes from GitHub to Disk.

## 7. Future Enhancements (Post-MVP)
- Support for `gitlab.com` or `bitbucket.org`.
- Verification of `SKILL.md` frontmatter before writing.
