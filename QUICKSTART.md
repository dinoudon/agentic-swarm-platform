# Quick Start Guide

## ⚡ Super Quick Start (No API Key!) - 2 minutes

**Don't have an API key? No problem!**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run in interactive mode (NO API KEY NEEDED)
python -m src.main run examples/sample_prd.md --backend interactive
```

That's it! See [CLAUDE_CODE_USAGE.md](CLAUDE_CODE_USAGE.md) for details.

---

## 📋 Standard Setup (With API Key) - 5 minutes

### 1. Install Dependencies

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install the platform
pip install -r requirements.txt
```

### 2. Configure API Key (Optional - Only for API Mode)

```bash
# Copy the example environment file
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env and add your Anthropic API key
# ANTHROPIC_API_KEY=sk-ant-...
```

Get your API key from: https://console.anthropic.com/

**OR skip this step and use `--backend interactive` instead!**

### 3. Test the Installation

```bash
# View configuration
python -m src.main config-info

# Analyze the sample PRD (dry run - no API calls for execution)
python -m src.main analyze examples/sample_prd.md
```

## Your First Execution

### Option 1: Interactive Mode (No API Key)

```bash
# Execute with interactive backend
python -m src.main run examples/sample_prd.md --backend interactive --output ./my-output
```

You'll see tasks displayed one by one. Ask Claude Code (me!) to complete them!

### Option 2: API Mode (Requires API Key)

```bash
# Execute with Anthropic API (fully automated)
python -m src.main run examples/sample_prd.md --backend anthropic --output ./my-output
```

This will:
1. Parse the PRD about a user authentication system
2. Use Claude to slice it into ~10-15 tasks
3. Spawn multiple specialized agents
4. Execute tasks in parallel
5. Generate code, docs, tests, and analysis
6. Save everything to `./my-output`

Expected output structure:
```
my-output/
├── summary.md           # Executive summary of what was built
├── metrics.json         # Cost and performance metrics
├── code/               # Generated authentication code
├── documentation/      # API docs and guides
├── analysis/          # Architecture analysis
└── test/              # Test suites
```

### Estimated Cost & Time

For the sample PRD:
- **Tokens**: ~100-150K tokens
- **Cost**: ~$2-3 USD with Claude Opus (or ~$0.50 with Sonnet)
- **Time**: 2-5 minutes depending on complexity

## Next Steps

### Create Your Own PRD

1. Create a new markdown file (e.g., `my-project.md`)
2. Structure it with clear sections:
   - Overview
   - Requirements
   - Technical Details
   - API Specifications (if applicable)
   - Testing Requirements
   - etc.

3. Run it:
```bash
python -m src.main run my-project.md --output ./my-project-output
```

### Customize Configuration

Edit `config/default.yaml` or use environment variables:

```bash
# Use Sonnet for lower cost
export ANTHROPIC__DEFAULT_MODEL=claude-sonnet-4-5-20250929

# Increase agents for faster execution
export AGENT_POOL__MAX_AGENTS=10

# Change output directory
export MONITORING__OUTPUT_DIRECTORY=/path/to/output
```

### Analyze Before Executing

Always check the task breakdown first:

```bash
python -m src.main analyze my-project.md
```

This shows you what tasks will be created without spending API credits.

## Common Use Cases

### 1. Generate a Complete API

PRD should include:
- API endpoints with request/response formats
- Data models
- Authentication requirements
- Error handling

Result: Code + docs + tests for all endpoints

### 2. Design System Architecture

PRD should include:
- System requirements
- Scale requirements
- Technology preferences
- Integration points

Result: Comprehensive architecture analysis + recommendations

### 3. Create Documentation

PRD should include:
- Product overview
- Features to document
- Target audience
- Examples needed

Result: Complete documentation suite

### 4. Generate Test Suites

PRD should include:
- Components to test
- Test scenarios
- Coverage requirements

Result: Unit and integration tests

## Troubleshooting

### "ANTHROPIC_API_KEY not found"

Make sure you:
1. Created the `.env` file
2. Added your API key
3. Restarted your terminal/shell

### Tasks failing repeatedly

Check the logs for specific errors. Common issues:
- API rate limits (reduce `max_concurrent_requests`)
- Invalid PRD format (make sure it's valid markdown)
- Network issues (check connectivity)

### Out of budget

Use Sonnet instead of Opus:
```bash
export ANTHROPIC__DEFAULT_MODEL=claude-sonnet-4-5-20250929
```

Or analyze first to estimate costs:
```bash
python -m src.main analyze your-prd.md
# Review task count, then decide
```

## Tips for Better Results

1. **Be Specific**: More detailed PRDs produce better results
2. **Structure Well**: Use clear headings and sections
3. **Include Examples**: Examples help Claude understand intent
4. **Specify Tech Stack**: Mention languages, frameworks, tools
5. **Define Success Criteria**: Clear acceptance criteria improve output quality

## Getting Help

- Read the full [README.md](README.md)
- Check [examples/sample_prd.md](examples/sample_prd.md) for inspiration
- Review your output in `summary.md` for insights
- Check logs for detailed error messages

## What's Next?

The platform generates everything you need to start building:
1. Review the generated code in `output/code/`
2. Read the architecture analysis in `output/analysis/`
3. Check the API documentation in `output/documentation/`
4. Run the tests in `output/test/`

You can then:
- Refine the code manually
- Use it as a starting point for your project
- Run another iteration with a refined PRD
- Generate additional components

Happy building! 🚀
