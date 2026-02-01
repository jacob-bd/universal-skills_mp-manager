# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains the **Universal Skill Manager** skill, which acts as a centralized package manager for AI capabilities across multiple AI coding tools (Gemini CLI, Google Anti-Gravity, OpenCode, Claude Code, Cursor, etc.).

The skill enables:
- **Discovery**: Searching for skills from SkillsMP.com using keyword or AI semantic search
- **Installation**: Installing skills from GitHub to User-level (global) or Project-level (local) scopes
- **Synchronization**: Copying/syncing skills across different AI tools
- **Consistency**: Maintaining version consistency across installed locations

## Architecture

This is a **skill definition repository** containing the Universal Skill Manager in the `universal-skill-manager/` subfolder. It is not a traditional codebase with source files.

### Repository Structure

```
skillsmp-universal-skills-manager/
├── README.md                       # Installation & usage documentation
├── CLAUDE.md                       # This file - technical context
├── specs.md                        # Technical specification for install script
└── universal-skill-manager/        # The skill folder
    ├── SKILL.md                    # Skill definition and logic
    └── scripts/
        └── install_skill.py        # Python helper for downloading skills from GitHub
```

### Skill Structure

The `SKILL.md` file follows this format:
- **Frontmatter**: YAML metadata (name, description)
- **Documentation**: Markdown content describing when to use the skill, capabilities, operational rules
- **Implementation details**: Instructions for the AI agent on how to execute skill functionality

### Supported Tool Ecosystem

The skill manages skills across these AI tools and their respective paths:

| Tool | User Scope (Global) | Project Scope (Local) |
|------|---------------------|----------------------|
| Gemini CLI | `~/.gemini/skills/` | `./.gemini/skills/` |
| Google Anti-Gravity | `~/.gemini/antigravity/skills/` | `./.antigravity/extensions/` |
| OpenCode | `~/.config/opencode/skills/` | `./.opencode/skills/` |
| Claude Code | `~/.claude/skills/` | `./.claude/skills/` |
| OpenAI Codex | `~/.codex/skills/` | `./.codex/skills/` |

| block/goose | `~/.goose/agents/` | `./.goose/agents/` |
| Roo Code | `~/.roo/skills/` | `./.roo/skills/` |
| Cursor | `~/.cursor/extensions/` | `./.cursor/extensions/` |

## Key Concepts

### SkillsMP API Integration

The skill uses the SkillsMP.com API to discover skills:

**API Endpoints:**
- **Keyword Search**: `/api/v1/skills/search?q={query}&limit=20&sortBy=recent|stars`
- **AI Semantic Search**: `/api/v1/skills/ai-search?q={query}`

**Authentication:**
- Bearer token required via `SKILLSMP_API_KEY` environment variable
- Header format: `Authorization: Bearer $SKILLSMP_API_KEY`
- Configuration options:
  - Shell profile: `export SKILLSMP_API_KEY="your_key"` in `~/.zshrc` or `~/.bashrc`
  - Home directory .env: Create `~/.env` with the API key, then `source ~/.env`
  - Session-based: `export SKILLSMP_API_KEY="your_key"` (temporary)

**Response Fields:**
- `id`, `name`, `author`, `description`
- `githubUrl` (for fetching skill content)
- `skillUrl` (web page URL)
- `stars`, `updatedAt`

**Content Fetching:**
Skills are stored in GitHub repositories. To get the actual SKILL.md content:
1. Extract from `githubUrl`: `https://github.com/{user}/{repo}/tree/{branch}/{path}`
2. Convert to raw URL: `https://raw.githubusercontent.com/{user}/{repo}/{branch}/{path}/SKILL.md`
3. Fetch using curl or web_fetch

### Skill Installation Flow

When installing a skill, the manager:
1. Identifies the source (SkillsMP API search result or local file)
2. Fetches skill content from GitHub (converts tree URL to raw URL)
3. Determines target scope (User/Global vs Project/Local)
4. Performs a "Sync Check" to detect other installed AI tools
5. Offers to sync the skill across all detected tools
6. Creates the skill directory structure: `.../skills/{skill-name}/SKILL.md`

### Skill Discovery

Skills are discovered using the SkillsMP.com API:
- **Keyword Search**: Direct term matching, supports pagination and sorting
- **AI Semantic Search**: Natural language queries with relevance scoring
- **Method**: API calls using curl/bash, parse JSON responses, display results with metadata (author, stars, description)

### Synchronization Logic

The skill maintains consistency by:
- Comparing modification times or content across all installed locations
- Reporting version mismatches
- Offering to overwrite older versions with newer ones

## Working with This Repository

### File Locations

- **Skill definition**: `universal-skill-manager/SKILL.md` - The main skill logic and instructions
- **Install helper**: `universal-skill-manager/scripts/install_skill.py` - Python script for downloading skills from GitHub
- **User documentation**: `README.md` - Installation, configuration, and usage guide
- **Developer context**: `CLAUDE.md` - This file, technical architecture and guidelines

### Testing Changes

When modifying the skill:
1. Edit `universal-skill-manager/SKILL.md`
2. Verify environment variable `SKILLSMP_API_KEY` is set
3. Test API calls manually using curl (examples in README)
4. Install the modified skill locally to test: `cp -r universal-skill-manager ~/.claude/skills/`
5. Test discovery, installation, and sync workflows

## Development Guidelines

### Modifying the Skill

When editing `SKILL.md`:
- Maintain YAML frontmatter validity (name, description fields)
- Keep the structure: frontmatter → usage triggers → capabilities → operational rules
- Ensure instructions are clear for AI agent execution
- Test that the markdown renders correctly

### Adding New AI Tool Support

To add a new AI tool:
1. Add the tool to the ecosystem table in SKILL.md
2. Specify both User-level and Project-level paths
3. Document any tool-specific requirements (manifest files, naming conventions)
4. Update the "Cross-Platform Adaptation" section if the tool requires special handling

### Installed Skill Directory Structure

When the Universal Skill Manager installs a skill, it creates this structure in the target AI tool:
```
~/.claude/skills/{skill-name}/     # Or other tool's path
  ├── SKILL.md (required)
  ├── Reference docs (optional)
  ├── Scripts (optional)
  └── Config files (optional)
```

For example, installing "code-debugging" creates:
```
~/.claude/skills/code-debugging/SKILL.md
```

## Important Notes

- **API Key Required**: The `SKILLSMP_API_KEY` environment variable must be set for skill discovery to work. See README.md for configuration instructions.
- **Root Directory Safety**: The install script will abort with exit code 4 if the destination appears to be a root skills directory (contains skills but no SKILL.md). This prevents accidental data loss.
- **Update Comparison**: When updating an existing skill, the script compares files and shows a diff before overwriting, prompting for confirmation.
- **No overwriting without confirmation**: Always ask before overwriting existing skills unless "--force" is explicitly used
- **Structure integrity**: Never dump loose files into the root skills directory; always create a dedicated folder per skill
- **Cross-platform compatibility**: Some tools (OpenCode, Anti-Gravity) may require additional manifest files generated from SKILL.md frontmatter
- **GitHub content fetching**: Skills are fetched from GitHub using raw URLs converted from the tree URLs provided by SkillsMP API
