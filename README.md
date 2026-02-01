# Universal Skills(mp) Manager

<p align="center">
  <img src="assets/mascot.jpeg" alt="Universal Skills(mp) Manager" width="100%">
</p>

<p align="center">
  <a href="https://skillsmp.com">Powered by SkillsMP.com</a> • 
  <a href="#quick-start">Quick Start</a> • 
  <a href="#features">Features</a> • 
  <a href="#supported-tools">Supported Tools</a>
</p>

---

A centralized skill manager for AI coding assistants. Discovers, installs, and synchronizes skills from [SkillsMP.com](https://skillsmp.com) across multiple AI tools including Claude Code, OpenAI Codex, Gemini CLI, and more.

## Features

- 🔍 **Search & Discover**: Find skills using keyword or AI semantic search via SkillsMP API
- 📦 **One-Click Install**: Download and validate skills with atomic installation (temp → validate → install)
- 🔄 **Cross-Tool Sync**: Automatically sync skills across all your installed AI tools
- 📊 **Skill Matrix Report**: See which skills are installed on which tools at a glance
- ✅ **Multi-File Validation**: Validates `.py`, `.sh`, `.json`, `.yaml` files during install
- 🌍 **Global Installation**: User-level skills available across all projects

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/jacob-bd/universal-skills_mp-manager.git
cd universal-skills_mp-manager
```

### Step 2: Copy to Your AI Tool

Copy the `universal-skill-manager` folder to your tool's skills directory:

| Tool | Global Path |
|------|-------------|
| **OpenAI Codex** | `~/.codex/skills/` |
| **Claude Code** | `~/.claude/skills/` |
| **Gemini CLI** | `~/.gemini/skills/` |
| **Google Antigravity** | `~/.gemini/antigravity/skills/` |
| **Cursor** | `~/.cursor/extensions/` |
| **Roo Code** | `~/.roo/skills/` |
| **OpenCode** | `~/.config/opencode/skills/` |
| **OpenClaw** | `~/.openclaw/workspace/skills/` |
| **block/goose** | `~/.config/goose/skills/` |

```bash
# Example: Install to OpenAI Codex
cp -r universal-skill-manager ~/.codex/skills/

# Example: Install to Claude Code
cp -r universal-skill-manager ~/.claude/skills/

# Example: Install to Gemini CLI
cp -r universal-skill-manager ~/.gemini/skills/

# Example: Install to OpenClaw
cp -r universal-skill-manager ~/.openclaw/workspace/skills/
```

### Step 3: Restart Your AI Assistant

Restart or reload your AI tool to pick up the new skill.

## Quick Start

Once installed, just ask your AI assistant:

```
"Search for a debugging skill"
"Install the humanizer skill"
"Show me my skill report"
"Sync the skill-creator to all my tools"
"What skills do I have in Codex vs Claude?"
```

### Using the Install Script

The skill includes a Python helper script for downloading skills from GitHub:

```bash
# Preview what would be downloaded (dry-run)
python3 path/to/install_skill.py \
  --url "https://github.com/user/repo/tree/main/skill-folder" \
  --dest "~/.codex/skills/my-skill" \
  --dry-run

# Actually install to your preferred tool
python3 path/to/install_skill.py \
  --url "https://github.com/user/repo/tree/main/skill-folder" \
  --dest "~/.gemini/skills/my-skill" \
  --force
```

**Script features:**
- Zero dependencies (Python 3 stdlib only)
- Atomic install (downloads to temp, validates, then copies to destination)
- Safety check prevents accidental targeting of root skills directories
- Compares new vs existing skills before update (shows diff)
- Validates `.py`, `.sh`, `.json`, `.yaml` files
- Supports subdirectories and nested files

## Configuration

### API Key Setup

The Universal Skill Manager requires a SkillsMP API key to search and discover skills.

#### Option 1: Shell Profile (Recommended)

Add the API key to your shell profile to make it available globally across all sessions:

```bash
# For Zsh users (macOS default)
echo 'export SKILLSMP_API_KEY="your_api_key_here"' >> ~/.zshrc
source ~/.zshrc

# For Bash users
echo 'export SKILLSMP_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

This ensures the API key is always available when you use any AI tool.

#### Option 2: .env File in Home Directory

Create a `.env` file in your home directory:

```bash
# Create ~/.env
cat > ~/.env << 'EOF'
SKILLSMP_API_KEY=your_api_key_here
EOF
```

Then load it before using AI tools:

```bash
# Load .env file
source ~/.env

# Or add to your shell profile to auto-load
echo 'source ~/.env' >> ~/.zshrc
```

#### Option 3: Session-based (Temporary)

For temporary use in a single terminal session:

```bash
export SKILLSMP_API_KEY="your_api_key_here"
```

**Note**: This only persists for the current terminal session.

#### Windows Users

For Windows (PowerShell):
```powershell
[System.Environment]::SetEnvironmentVariable('SKILLSMP_API_KEY', 'your_api_key_here', 'User')
```
*Restart your terminal for changes to take effect.*

For Windows (Command Prompt):
```cmd
setx SKILLSMP_API_KEY "your_api_key_here"
```

#### Getting Your API Key

1. Visit [SkillsMP.com](https://skillsmp.com)
2. Navigate to the API section
3. Generate or copy your API key
4. Configure using one of the methods above

#### Verify API Key Setup

After configuration, verify the API key is set correctly:

```bash
# Check if the environment variable is set
echo $SKILLSMP_API_KEY

# Test the API connection
curl -X GET "https://skillsmp.com/api/v1/skills/search?q=test&limit=1" \
  -H "Authorization: Bearer $SKILLSMP_API_KEY"
```

If configured correctly, you should see a JSON response with skill data.

## Usage

Once installed, the skill activates automatically when you:

### Search for Skills

```
"Find a debugging skill"
"Search for React skills"
"Show me skills for testing"
```

The AI will search SkillsMP.com and display relevant skills with:
- Skill name and author
- Description
- Star rating
- GitHub repository link

### Install Skills

After search results appear:

```
"Install the code-debugging skill"
"Install skill #3 from the results"
```

The AI will:
1. Ask whether to install globally or locally
2. Fetch the skill content from GitHub
3. Detect other installed AI tools
4. Offer to sync the skill across all tools
5. Install and confirm success

### Sync Skills

```
"Sync the debugging skill to Cursor"
"Copy this skill to all my AI tools"
```

### Manage Skills

```
"Show my installed skills"
"Update the debugging skill"
"Remove the old React skill"
```

## How It Works

1. **Discovery**: The AI queries the SkillsMP.com API using keyword or semantic search
2. **Selection**: You choose which skill to install from the results
3. **Fetching**: The AI fetches the SKILL.md content from the skill's GitHub repository
4. **Installation**: Creates the proper directory structure (`~/.claude/skills/{skill-name}/`)
5. **Synchronization**: Optionally copies to other detected AI tools

## Supported Tools

| AI Tool | Global Path | Local Path |
|---------|-------------|------------|
| **Claude Code** | `~/.claude/skills/` | `./.claude/skills/` |
| **Cursor** | `~/.cursor/extensions/` | `./.cursor/extensions/` |
| **Gemini CLI** | `~/.gemini/skills/` | `./.gemini/skills/` |
| **Google Anti-Gravity** | `~/.gemini/antigravity/skills/` | `./.antigravity/extensions/` |
| **OpenCode** | `~/.config/opencode/skills/` | `./.opencode/skills/` |
| **OpenClaw** | `~/.openclaw/workspace/skills/` | `./.openclaw/skills/` |
| **OpenAI Codex** | `~/.codex/skills/` | `./.codex/skills/` |
| **block/goose** | `~/.config/goose/skills/` | `./.goose/agents/` |
| **Roo Code** | `~/.roo/skills/` | `./.roo/skills/` |

## API Reference

### Search Endpoints

**Keyword Search**
```bash
curl -X GET "https://skillsmp.com/api/v1/skills/search?q=debugging&limit=20&sortBy=recent" \
  -H "Authorization: Bearer $SKILLSMP_API_KEY"
```

**AI Semantic Search**
```bash
curl -X GET "https://skillsmp.com/api/v1/skills/ai-search?q=help+me+debug+code" \
  -H "Authorization: Bearer $SKILLSMP_API_KEY"
```

### Response Format

```json
{
  "success": true,
  "data": {
    "skills": [
      {
        "id": "skill-id",
        "name": "code-debugging",
        "author": "AuthorName",
        "description": "Systematic debugging methodology...",
        "githubUrl": "https://github.com/user/repo/tree/main/skills/code-debugging",
        "stars": 15,
        "updatedAt": 1768838561
      }
    ]
  }
}
```

## Repository Structure

```
skillsmp-universal-skills-manager/
├── README.md                        # This file
├── CLAUDE.md                        # Claude Code context file
├── specs.md                         # Technical specification
└── universal-skill-manager/         # The skill itself
    ├── SKILL.md                     # Skill definition and logic
    └── scripts/
        └── install_skill.py         # Helper script for downloading skills
```

## Contributing

Skills are sourced from the community via [SkillsMP.com](https://skillsmp.com). To contribute:

1. Create your skill with proper YAML frontmatter
2. Host it on GitHub
3. Submit to SkillsMP.com for indexing

## License

MIT License - See repository for details

## Support

- **Issues**: Report bugs or request features via GitHub Issues
- **SkillsMP**: Visit [skillsmp.com](https://skillsmp.com) for skill discovery
- **Documentation**: See `CLAUDE.md` for technical details

---

**Note**: This skill requires an active internet connection to search SkillsMP.com and fetch skill content from GitHub.

## Acknowledgments

This skill was inspired by the [skill-lookup](https://skillsmp.com/skills/f-prompts-chat-plugins-claude-prompts-chat-skills-skill-lookup-skill-md) skill by f-prompts.

