# Complete Usage Guide - Agentic Swarm Platform

## 🚀 Quick Start (5 Minutes)

### Option A: Without API Key (Interactive Mode) - FREE!

```bash
# 1. Clone the repository
git clone https://github.com/dinoudon/agentic-swarm-platform.git
cd agentic-swarm-platform

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the sample PRD (NO API KEY NEEDED!)
python -m src.main run examples/sample_prd.md --backend interactive

# 4. When tasks appear, ask Claude Code to execute them
```

### Option B: With API Key (Automated Mode) - FAST!

```bash
# 1. Clone the repository
git clone https://github.com/dinoudon/agentic-swarm-platform.git
cd agentic-swarm-platform

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your API key
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=your-key-here

# 4. Run the sample PRD (fully automated!)
python -m src.main run examples/sample_prd.md --backend anthropic
```

---

## 📋 Detailed Instructions

### Example 1: Analyze a PRD (No Execution)

```bash
python -m src.main analyze examples/sample_prd.md
```

Shows task breakdown without executing anything.

### Example 2: Run with Interactive Mode

```bash
python -m src.main run examples/sample_prd.md --backend interactive --output ./my-output
```

### Example 3: Run with API (Automated)

```bash
python -m src.main run examples/sample_prd.md --backend anthropic --output ./output
```

### Example 4: Custom PRD

Create your own PRD file and run it:

```bash
# Create PRD
echo "# My Project

## Overview
Build a REST API...

## Requirements
- Feature 1
- Feature 2" > my-project.md

# Run it
python -m src.main run my-project.md --backend interactive
```

---

## 📊 Output Structure

```
output/
├── summary.md           # Executive summary
├── metrics.json         # Performance metrics
├── code/               # Generated code
├── documentation/      # Docs
├── analysis/          # Architecture analysis
└── test/              # Tests
```

---

## ⚙️ Configuration

### CLI Options

```bash
python -m src.main run --help

Options:
  --backend [anthropic|interactive]  Execution backend
  --output, -o PATH                  Output directory
  --max-agents INTEGER               Max agents
  --dry-run                          Analyze only
  --log-level TEXT                   Logging level
```

### Environment Variables

Create `.env`:

```bash
ANTHROPIC_API_KEY=your-key-here
BACKEND__TYPE=interactive
ANTHROPIC__DEFAULT_MODEL=claude-sonnet-4-5-20250929
AGENT_POOL__MAX_AGENTS=5
```

---

## 💰 Cost Estimates

**Using Sonnet (default):**
- Small PRD (5 tasks): ~$0.15-0.25
- Medium PRD (10-15 tasks): ~$0.50-0.75
- Large PRD (20+ tasks): ~$1-2

**Interactive mode:** FREE (no API costs)

---

## 🐛 Common Issues

**"API key not found"**
→ Use `--backend interactive` (no key needed)

**"Module not found"**
→ Run `pip install -r requirements.txt`

**Tasks failing**
→ Check logs with `--log-level DEBUG`

**Rate limits**
→ Reduce `max_agents` or use interactive mode

---

## 📚 More Resources

- **QUICKSTART.md** - 2-minute setup
- **CLAUDE_CODE_USAGE.md** - Interactive mode guide
- **README.md** - Full documentation
- **examples/sample_prd.md** - Example PRD

---

## 🎯 Tips

1. Always run `analyze` first to see what tasks will be created
2. Use interactive mode for learning
3. Use API mode for production
4. Start with small PRDs
5. Check `output/summary.md` for insights

---

**Repository:** https://github.com/dinoudon/agentic-swarm-platform

**Happy building!** 🚀
