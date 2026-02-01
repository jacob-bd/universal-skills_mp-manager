---
name: universal-skill-manager
description: The master coordinator for AI skills. Discovers skills from SkillsMP.com, manages installation, and synchronization across Claude Code, Gemini CLI, Google Anti-Gravity, OpenCode, and other AI tools. Handles User-level (Global) and Project-level (Local) scopes.
---

# Universal Skill Manager

This skill empowers the agent to act as a centralized package manager for AI capabilities. It discovers skills from the SkillsMP.com repository and unifies skill management across multiple AI tools (Claude Code, Gemini, Anti-Gravity, OpenCode, Continue, Cursor, etc.), ensuring consistency and synchronization.

## When to Use This Skill

Activate this skill when the user:
- Wants to **find or search** for new skills.
- Wants to **install** a skill (from a search result or local file).
- Wants to **sync** skills between different AI tools (e.g., "Copy this Gemini skill to OpenCode").
- Asks to **move or copy** skills between scopes (User vs. Project).
- Mentions "Google Anti-Gravity", "OpenCode", or "Gemini" in the context of skills/extensions.

## Supported Ecosystem

This skill manages the following tools and scopes. Always verify these paths exist before acting.

| Tool | User Scope (Global) | Project Scope (Local) |
| :--- | :--- | :--- |
| **Gemini CLI** | `~/.gemini/skills/` | `./.gemini/skills/` |
| **Google Anti-Gravity** | `~/.antigravity/extensions/` | `./.antigravity/extensions/` |
| **OpenCode** | `~/.opencode/extensions/` | `./.opencode/skills/` |
| **OpenClaw** | `~/.openclaw/workspace/skills/` | `./.openclaw/skills/` |
| **Claude Code** | `~/.claude/skills/` | `./.claude/skills/` |
| **OpenAI Codex** | `~/.codex/skills/` | `./.codex/skills/` |
| **Continue** | `~/.continue/prompts/` | `./.continue/prompts/` |
| **block/goose** | `~/.goose/agents/` | `./.goose/agents/` |
| **Roo Code** | `~/.roo/skills/` | `./.roo/skills/` |
| **Cursor** | `~/.cursor/extensions/` | `./.cursor/extensions/` |
| **OpenClaw** | `~/.openclaw/skills/` | `./.openclaw/skills/` |
| **OpenClaw** | `~/.openclaw/workspace/skills/` | `./.openclaw/skills/` |

*(Note: If a tool uses a different directory structure, ask the user to confirm the path, then remember it using `save_memory`.)*

## Core Capabilities

### 1. Smart Installation & Synchronization
**Trigger:** User asks to install a skill (e.g., "Install the debugging skill" or "Install skill ID xyz").

**Procedure:**
1.  **Identify Source:**
    *   If from SkillsMP search result: Use the `githubUrl` from the API response
    *   If from skill name/ID: Search SkillsMP API first to find the skill
    *   If local: Identify the source path
2.  **Verify Repository Structure (CRITICAL):**
    *   Before downloading, browse the GitHub repo to confirm the skill folder location
    *   Use GitHub API to list directory contents: `GET /repos/{owner}/{repo}/contents?ref={branch}`
    *   Look for folders containing `SKILL.md` - this is the actual skill directory
    *   Common patterns: `skill/`, `skills/{name}/`, root level, or custom folder names
    *   Confirm the correct path before generating the download URL
3.  **Download Using Helper Script:**
    *   Use `install_skill.py` (located in this skill's `scripts/` folder):
    ```bash
    python3 ~/.claude/skills/universal-skill-manager/scripts/install_skill.py \
      --url "https://github.com/{owner}/{repo}/tree/{branch}/{skill-folder}" \
      --dest "{target-path}" \
      --dry-run  # Preview first, then remove flag to install
    ```
    *   The script handles: atomic install, validation, subdirectories, backups
4.  **Determine Primary Target:**
    *   Ask: "Should this be installed Globally (User) or Locally (Project)?"
    *   Determine the primary tool (e.g., if user is in Claude Code, Claude is primary)
5.  **The "Sync Check" (CRITICAL):**
    *   **Scan:** Check if other supported tools are installed on the system (look for their config folders)
    *   **Propose:** "I see you also have OpenCode and Cursor installed. Do you want to sync this skill to them as well?"
6.  **Execute:**
    *   Run the install script for each target location
    *   Ensure the standard structure is maintained
7.  **Report Success:**
    *   Show installed skill name, author, and location(s)
    *   Display GitHub URL and stars count for reference

### 2. The "Updates & Consistency" Check
**Trigger:** User modifies a skill or asks to "sync" skills.

**Procedure:**
1.  **Compare:** Check the modification times or content of the skill across all installed locations.
2.  **Report:** "The 'code-review' skill in Gemini is newer than the one in OpenCode."
3.  **Action:** Offer to overwrite older versions with the newer version to ensure consistency.

### 3. Skill Discovery (SkillsMP API)
**Trigger:** User searches for skills (e.g., "Find a debugging skill" or "Search for React skills").

**Procedure:**
1.  **Check API Key (FIRST):**
    *   Verify `SKILLSMP_API_KEY` is set: `echo $SKILLSMP_API_KEY`
    *   If not set, guide the user:
        1. Visit [SkillsMP.com](https://skillsmp.com) and navigate to API section
        2. Generate or copy API key
        3. Set it permanently:
           ```bash
           echo 'export SKILLSMP_API_KEY="your_key_here"' >> ~/.zshrc
           source ~/.zshrc
           ```
    *   Do NOT proceed with search until key is configured
2.  **Choose Search Method:**
    -   **Keyword Search** (`/api/v1/skills/search`): For specific terms, exact matches
    -   **AI Semantic Search** (`/api/v1/skills/ai-search`): For natural language queries (e.g., "help me debug code")

2.  **Execute API Call:**
    ```bash
    # Keyword Search
    curl -X GET "https://skillsmp.com/api/v1/skills/search?q={query}&limit=20&sortBy=recent" \
      -H "Authorization: Bearer $SKILLSMP_API_KEY"

    # AI Semantic Search (for natural language queries)
    curl -X GET "https://skillsmp.com/api/v1/skills/ai-search?q={query}" \
      -H "Authorization: Bearer $SKILLSMP_API_KEY"
    ```

    **Note:** The `SKILLSMP_API_KEY` environment variable must be set. Users can set it via:
    - Session: `export SKILLSMP_API_KEY="your_api_key"`
    - Shell profile: Add to `~/.bashrc` or `~/.zshrc`
    - .env file: Create `.env` with `SKILLSMP_API_KEY=your_api_key`

3.  **Parse Response:**
    -   **Keyword Search Response:** Extract from `data.skills[]` array
    -   **AI Search Response:** Extract from `data.data[]` array, check for `skill` object
    -   Available fields: `id`, `name`, `author`, `description`, `githubUrl`, `skillUrl`, `stars`, `updatedAt`

4.  **Display Results:**
    -   Show skill name, author, stars, and description
    -   Include GitHub URL for reference
    -   For AI search: Show relevance score
    -   Limit to top 10-15 results for readability

5.  **Offer Installation:**
    -   After displaying results, ask: "Which skill would you like to install?"
    -   Note the skill's `githubUrl` for content fetching

### 4. Skill Matrix Report
**Trigger:** User asks for skill report/overview (e.g., "Show my skills", "What skills do I have?", "Skill report", "Compare my tools").

**Procedure:**
1.  **Detect Installed Tools:**
    Check which AI tools are installed by verifying their user-level skills directories exist:
    ```bash
    # Check each tool's skills directory
    ls -d ~/.claude/skills 2>/dev/null && echo "Claude: ✓"
    ls -d ~/.codex/skills 2>/dev/null && echo "Codex: ✓"
    ls -d ~/.gemini/skills 2>/dev/null && echo "Gemini: ✓"
    ls -d ~/.gemini/antigravity/skills 2>/dev/null && echo "Antigravity: ✓"
    ls -d ~/.openclaw/workspace/skills 2>/dev/null && echo "OpenClaw: ✓"
    ls -d ~/.continue/prompts 2>/dev/null && echo "Continue: ✓"
    ls -d ~/.cursor/skills 2>/dev/null && echo "Cursor: ✓"
    ls -d ~/.opencode/skills 2>/dev/null && echo "OpenCode: ✓"
    ls -d ~/.roo/skills 2>/dev/null && echo "Roo: ✓"
    ```

2.  **Collect All Skills:**
    For each detected tool, list skill folders:
    ```bash
    find ~/.{claude,codex,gemini,gemini/antigravity,openclaw/workspace}/skills -maxdepth 1 -type d 2>/dev/null | \
      xargs -I{} basename {} | sort -u
    ```

3.  **Generate Matrix Table:**
    Create a markdown table where:
    - **Rows** = skill names (deduplicated across all tools)
    - **Columns** = only tools that are installed on the system
    - **Cells** = ✅ (installed) or ❌ (not installed)

    Example output:
    ```
    | Skill | Claude | Codex | Gemini |
    |-------|--------|-------|--------|
    | humanizer | ✅ | ❌ | ✅ |
    | skill-creator | ❌ | ✅ | ❌ |
    | using-superpowers | ✅ | ✅ | ✅ |
    ```

4.  **Show Summary:**
    - Total skills across all tools
    - Skills unique to one tool
    - Skills installed everywhere

## Operational Rules

1.  **Structure Integrity:** When installing, always ensure the skill has its own folder (e.g., `.../skills/my-skill/`). Do not dump loose files into the root skills directory.
2.  **Conflict Safety:** If a skill already exists at a target location, **always** ask before overwriting, unless the user explicitly requested a "Force Sync."
3.  **OpenClaw Note:** OpenClaw may require a restart to pick up new skills if `skills.load.watch` is not enabled in `openclaw.json`. Warn the user of this after installation.
4.  **Cross-Platform Adaptation:**
    *   Gemini uses `SKILL.md`.
    *   If OpenCode or Anti-Gravity require a specific manifest (e.g., `manifest.json`), generate a basic one based on the `SKILL.md` frontmatter during installation.

## Available Tools
- `bash` (curl): Make API calls to SkillsMP.com, fetch skill content from GitHub.
- `web_fetch`: Fetch skill content from GitHub raw URLs (alternative to curl).
- `read_file` / `write_file`: Manage local skill files.
- `glob`: Find existing skills in local directories.

## Implementation Details

### Skill Structure
Skills typically contain:
- **SKILL.md** (required): Main instructions with frontmatter.
- **Reference docs**: Additional documentation files.
- **Scripts**: Helper scripts (Python, shell, etc.).
- **Config files**: JSON, YAML configurations.

### Installation Logic

#### A. Installing from SkillsMP API
1.  **Fetch Skill Content:**
    -   Convert `githubUrl` to raw content URL:
        ```
        Input:  https://github.com/{user}/{repo}/tree/{branch}/{path}
        Output: https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}/SKILL.md
        ```
    -   Fetch the SKILL.md content using curl or web_fetch

2.  **Create Directory:**
    -   Use skill `name` from API response for directory: `.../skills/{skill-name}/`
    -   Example: `.../skills/code-debugging/`

3.  **Save SKILL.md:**
    -   Write the fetched content to `SKILL.md` in the new directory
    -   Preserve the original YAML frontmatter and content

4.  **Handle Additional Files (Optional):**
    -   Check if GitHub repo has additional files (reference docs, scripts)
    -   Optionally fetch and save them to maintain complete skill package

5.  **Confirm:**
    -   Report: "Installed '{name}' by {author} to {path}"
    -   Show GitHub URL and stars count
    -   Offer sync to other AI tools

#### B. Installing from Local Source (Sync/Copy)
1.  **Retrieve:** Read all files from the source directory.
2.  **Create Directory:** Create the target directory `.../skills/{slug}/`.
3.  **Save Files:** Copy all files to the new location, preserving filenames.

### SkillsMP API Configuration

**Base URL:** `https://skillsmp.com/api/v1`

**Authentication:**
```bash
Authorization: Bearer $SKILLSMP_API_KEY
```

**Available Endpoints:**
- `GET /api/v1/skills/search?q={query}&page={1}&limit={20}&sortBy={recent|stars}`
- `GET /api/v1/skills/ai-search?q={query}`

**Response Format (Keyword Search):**
```json
{
  "success": true,
  "data": {
    "skills": [
      {
        "id": "...",
        "name": "skill-name",
        "author": "AuthorName",
        "description": "...",
        "githubUrl": "https://github.com/user/repo/tree/main/path",
        "skillUrl": "https://skillsmp.com/skills/...",
        "stars": 10,
        "updatedAt": 1768838561
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 3601,
      "totalPages": 1801,
      "hasNext": true
    }
  }
}
```

**Response Format (AI Search):**
```json
{
  "success": true,
  "data": {
    "search_query": "...",
    "data": [
      {
        "file_id": "...",
        "filename": "...",
        "score": 0.656,
        "skill": {
          "id": "...",
          "name": "...",
          "author": "...",
          "description": "...",
          "githubUrl": "...",
          "skillUrl": "...",
          "stars": 0,
          "updatedAt": 1769542668
        }
      }
    ]
  }
}
```

**Error Handling:**
- `401`: Invalid or missing API key
- `400`: Missing required query parameter
- `500`: Internal server error

### Guidelines
-   **Search First:** Always use the SkillsMP API to discover available skills.
-   **Prefer AI Search:** For natural language queries, use `/ai-search` for better relevance.
-   **Verify Content:** After fetching from GitHub, verify the SKILL.md has valid YAML frontmatter.
-   **Structure Integrity:** Maintain the `.../skills/{skill-name}/SKILL.md` structure.
-   **Syncing:** After installing a skill, offer to sync (copy) it to other detected AI tools.
-   **GitHub URLs:** Always convert tree URLs to raw.githubusercontent.com URLs for content fetching.