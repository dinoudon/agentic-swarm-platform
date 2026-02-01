# Agentic Swarm Platform

A Python-based platform that uses Claude AI to automatically slice Product Requirements Documents (PRDs) into tasks and execute them in parallel using multiple specialized AI agents.

## Features

- **Automatic Task Slicing**: Claude analyzes PRDs and breaks them down into actionable tasks
- **Parallel Execution**: Multiple specialized agents work on tasks concurrently
- **Specialized Agents**:
  - Code Generation Agent
  - Documentation Agent
  - Analysis/Architecture Agent
  - Testing Agent
- **Dependency Management**: Tasks are executed in the correct order based on dependencies
- **Cost Tracking**: Real-time monitoring of token usage and API costs
- **Rich CLI**: Beautiful terminal interface with progress tracking
- **Comprehensive Output**: Organized artifacts (code, docs, tests, analysis)

## Quick Start

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd agentic-swarm-platform
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
# Or for development
pip install -e ".[dev]"
```

### 🎯 Two Ways to Use

#### Option A: Without API Key (Interactive Mode) - **RECOMMENDED FOR BEGINNERS**

No API key needed! Perfect if you're using Claude Code.

```bash
# Just run it!
python -m src.main run examples/sample_prd.md --backend interactive
```

See **[CLAUDE_CODE_USAGE.md](CLAUDE_CODE_USAGE.md)** for complete guide.

#### Option B: With API Key (Anthropic API)

For fully automated execution:

```bash
# 1. Configure API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 2. Run with API backend
python -m src.main run examples/sample_prd.md --backend anthropic
```

### Usage

#### Execute a PRD (Interactive Mode - No API Key)

```bash
python -m src.main run examples/sample_prd.md --backend interactive --output ./output
```

This will display tasks one-by-one for you to execute with Claude Code.

#### Execute a PRD (API Mode - Requires API Key)

```bash
python -m src.main run examples/sample_prd.md --backend anthropic --output ./output
```

This will:
1. Parse the PRD
2. Slice it into tasks using Claude
3. Execute tasks in parallel with multiple agents
4. Save results to `./output`

#### Analyze a PRD (Dry Run)

```bash
python -m src.main analyze examples/sample_prd.md
```

This shows the task breakdown without executing them.

#### View Configuration

```bash
python -m src.main config-info
```

### CLI Options

```bash
python -m src.main run [OPTIONS] PRD_FILE

Options:
  --output, -o PATH       Output directory (default: ./output)
  --backend TEXT          Backend: anthropic, claude-code, or interactive (default: interactive)
  --max-agents INTEGER    Override maximum number of agents
  --dry-run              Parse only, don't execute
  --config PATH          Path to custom config file
  --log-level TEXT       Logging level (default: INFO)
```

**Backend Options:**
- `anthropic` - Uses Anthropic API (requires API key, fast, automated)
- `claude-code` - Uses Claude Code CLI (no API key, automated if CLI available)
- `interactive` - Manual execution (no API key, you execute each task)

## Configuration

Configuration can be customized via:

1. **YAML file**: `config/default.yaml`
2. **Environment variables**: Override any setting using pattern `SECTION__KEY`

Example `.env`:
```bash
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC__MAX_TOKENS=8192
AGENT_POOL__MAX_AGENTS=10
MONITORING__LOG_LEVEL=DEBUG
```

### Configuration Sections

**Anthropic API**
- `default_model`: Claude model to use (default: claude-opus-4-5-20251101)
- `max_tokens`: Maximum tokens per response (default: 4096)
- `temperature`: Sampling temperature (default: 0.7)

**Rate Limiting**
- `max_requests_per_minute`: API request limit (default: 50)
- `max_tokens_per_minute`: Token limit (default: 200000)
- `max_concurrent_requests`: Concurrent request limit (default: 10)

**Agent Pool**
- `max_agents`: Maximum total agents (default: 5)
- `code_agent_count`: Number of code agents (default: 2)
- `docs_agent_count`: Number of doc agents (default: 1)
- `analysis_agent_count`: Number of analysis agents (default: 1)
- `test_agent_count`: Number of test agents (default: 1)

**Monitoring**
- `log_level`: Logging verbosity (default: INFO)
- `enable_cost_tracking`: Track API costs (default: true)
- `output_directory`: Where to save results (default: ./output)

## Output Structure

After execution, the output directory contains:

```
output/
├── summary.md              # Executive summary
├── metrics.json            # Execution metrics
├── code/                   # Generated code
│   ├── file1.py
│   └── file2.js
├── documentation/          # Generated docs
│   ├── api_docs.md
│   └── user_guide.md
├── analysis/               # Architecture analysis
│   └── architecture.md
└── test/                   # Generated tests
    ├── test_auth.py
    └── test_api.js
```

## Architecture

### Components

1. **PRD Parser**: Parses markdown PRDs and uses Claude to slice them into tasks
2. **Task Queue**: Manages task dependencies and execution order
3. **Agent Pool**: Creates and manages specialized agents
4. **Orchestrator**: Coordinates the entire execution flow
5. **Result Aggregator**: Combines results and generates summaries

### Execution Flow

```
1. Parse PRD from file
2. Slice into tasks (via Claude)
3. Validate task dependencies
4. Initialize agent pool
5. Execution loop:
   - Get ready tasks
   - Match tasks to available agents
   - Execute in parallel
   - Track progress
6. Aggregate results
7. Generate summary
8. Save artifacts
```

### Agent Specializations

- **Code Agent**: Generates production-ready code with best practices
- **Docs Agent**: Creates comprehensive documentation (API docs, guides)
- **Analysis Agent**: Performs architecture analysis and system design
- **Test Agent**: Writes unit and integration tests

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black src/

# Lint
ruff src/

# Type checking
mypy src/
```

### Project Structure

```
src/
├── main.py              # CLI entry point
├── core/                # Core orchestration
│   ├── orchestrator.py
│   ├── prd_parser.py
│   ├── task_queue.py
│   └── result_aggregator.py
├── agents/              # Agent implementations
│   ├── base_agent.py
│   ├── agent_pool.py
│   ├── code_agent.py
│   ├── docs_agent.py
│   ├── analysis_agent.py
│   └── test_agent.py
├── models/              # Data models
│   ├── prd.py
│   ├── task.py
│   ├── agent.py
│   ├── result.py
│   └── config.py
├── services/            # External services
│   ├── claude_client.py
│   ├── rate_limiter.py
│   └── cost_tracker.py
├── communication/       # Inter-agent communication
│   ├── event_bus.py
│   ├── state_manager.py
│   └── shared_context.py
└── utils/               # Utilities
    ├── logger.py
    ├── errors.py
    └── retry.py
```

## Cost Estimation

For a typical PRD (5-10 pages):
- PRD parsing: ~10K tokens
- Task execution: ~5-10K tokens per task
- 15 tasks: ~120K tokens total
- Summary generation: ~15K tokens

**Total**: ~150K tokens ≈ $2-3 USD (with Claude Opus)

Use Sonnet for lower costs (~$0.50-0.75 for same workload).

## Troubleshooting

**Issue**: API rate limit errors

**Solution**: Reduce `max_concurrent_requests` or `max_requests_per_minute` in config

---

**Issue**: Tasks failing

**Solution**: Check logs in console. Tasks are automatically retried up to 3 times.

---

**Issue**: Out of memory

**Solution**: Reduce `max_agents` to lower concurrent API calls

## Examples

### Simple PRD

See `examples/sample_prd.md` for a complete example of a user authentication system PRD.

### Custom Configuration

Create a custom config file:

```yaml
# my_config.yaml
anthropic:
  default_model: "claude-sonnet-4-5-20250929"
  max_tokens: 8192

agent_pool:
  max_agents: 10
  code_agent_count: 3
  docs_agent_count: 2
```

Run with custom config:
```bash
python -m src.main run my_prd.md --config my_config.yaml
```

## Roadmap

Future enhancements:
- [ ] Web UI dashboard
- [ ] Response caching
- [ ] Git integration (auto-commit)
- [ ] Custom agent plugins
- [ ] Result validation
- [ ] Multi-PRD support
- [ ] Human-in-the-loop approvals
- [ ] Cost optimization (model selection per task)

## License

MIT

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing documentation
- Review example PRDs
