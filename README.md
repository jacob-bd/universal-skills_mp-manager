# Universal Skill Manager

A centralized skill manager for AI coding assistants. Discovers, installs, and synchronizes skills from [SkillsMP.com](https://skillsmp.com) across multiple AI tools including Claude Code, Cursor, Continue, Gemini CLI, and more.

## Features

- 🔍 **Smart Discovery**: Search for skills using keyword or AI semantic search
- 📦 **Easy Installation**: Install skills from SkillsMP.com with a single command
- 🔄 **Cross-Tool Sync**: Automatically sync skills across all your AI tools
- 🌍 **Dual Scope**: Install globally (user-level) or locally (project-level)
- ⭐ **Community Curated**: Access thousands of skills from the SkillsMP community

## Installation

### Claude Code

1. Clone or copy the `universal-skill-manager` folder to your Claude skills directory:

```bash
# Global installation (recommended)
cp -r universal-skill-manager ~/.claude/agents/

# Project-level installation
cp -r universal-skill-manager ./.claude/agents/
```

2. Restart Claude Code or reload skills

### Cursor

```bash
# Global installation
cp -r universal-skill-manager ~/.cursor/extensions/

# Project-level installation
cp -r universal-skill-manager ./.cursor/extensions/
```

### Continue

```bash
# Global installation
cp -r universal-skill-manager ~/.continue/prompts/

# Project-level installation
cp -r universal-skill-manager ./.continue/prompts/
```

### Other AI Tools

See the [Supported Tools](#supported-tools) section for paths to other AI coding assistants.

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
| **Continue** | `~/.continue/prompts/` | `./.continue/prompts/` |
| **Gemini CLI** | `~/.gemini/skills/` | `./.gemini/skills/` |
| **Google Anti-Gravity** | `~/.antigravity/extensions/` | `./.antigravity/extensions/` |
| **OpenCode** | `~/.opencode/extensions/` | `./.opencode/skills/` |
| **OpenAI Codex** | `~/.codex/skills/` | `./.codex/skills/` |
| **block/goose** | `~/.goose/agents/` | `./.goose/agents/` |
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
skillsmp--skills-manager/
├── README.md                        # This file
├── CLAUDE.md                        # Claude Code context file
└── universal-skill-manager/         # The skill itself
    └── SKILL.md                     # Skill definition and logic
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

