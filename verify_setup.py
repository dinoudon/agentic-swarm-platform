#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verification script to check if the platform is set up correctly."""

import sys
import io
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def check_structure():
    """Check if all required directories and files exist."""
    print("Checking project structure...")

    required_files = [
        "src/main.py",
        "src/core/orchestrator.py",
        "src/core/prd_parser.py",
        "src/agents/base_agent.py",
        "src/agents/code_agent.py",
        "src/models/config.py",
        "config/default.yaml",
        "requirements.txt",
        "README.md",
        "examples/sample_prd.md",
    ]

    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)

    if missing:
        print("❌ Missing files:")
        for f in missing:
            print(f"  - {f}")
        return False
    else:
        print("✓ All required files present")
        return True


def check_imports():
    """Check if all required modules can be imported."""
    print("\nChecking Python imports...")

    required_modules = [
        ("anthropic", "Anthropic API client"),
        ("pydantic", "Pydantic"),
        ("click", "Click CLI"),
        ("rich", "Rich terminal UI"),
        ("yaml", "PyYAML"),
        ("dotenv", "Python-dotenv"),
        ("structlog", "Structlog"),
        ("tenacity", "Tenacity"),
        ("aiofiles", "Aiofiles"),
    ]

    missing = []
    for module, name in required_modules:
        try:
            __import__(module)
            print(f"✓ {name}")
        except ImportError:
            missing.append(name)
            print(f"❌ {name} not installed")

    if missing:
        print("\n❌ Missing dependencies. Install with:")
        print("  pip install -r requirements.txt")
        return False
    else:
        print("\n✓ All dependencies installed")
        return True


def check_env():
    """Check environment configuration."""
    print("\nChecking environment configuration...")

    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found")
        print("   This is OK if using --backend interactive")
        print("   For API mode: copy .env.example to .env and add ANTHROPIC_API_KEY")
        return True  # Not a failure - can use interactive mode

    # Read .env and check for API key
    with open(env_file) as f:
        content = f.read()

    if "ANTHROPIC_API_KEY=" in content and "your_api_key_here" not in content:
        # Check if it's not empty
        for line in content.split("\n"):
            if line.startswith("ANTHROPIC_API_KEY="):
                key = line.split("=", 1)[1].strip()
                if key and len(key) > 10:
                    print("✓ API key configured (can use --backend anthropic)")
                    return True

    print("ℹ️  ANTHROPIC_API_KEY not configured")
    print("   This is OK! Use --backend interactive (no API key needed)")
    print("   Or add API key for --backend anthropic")
    return True  # Still a pass - can use interactive mode


def check_config():
    """Check configuration loading."""
    print("\nChecking configuration loading...")

    try:
        from src.models.config import load_config

        config = load_config(Path("config/default.yaml"))
        print(f"✓ Configuration loaded successfully")
        print(f"  Model: {config.anthropic.default_model}")
        print(f"  Max Agents: {config.agent_pool.max_agents}")
        return True
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("Agentic Swarm Platform - Setup Verification")
    print("=" * 60)

    checks = [
        ("Project Structure", check_structure),
        ("Dependencies", check_imports),
        ("Environment", check_env),
        ("Configuration", check_config),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {name} check failed with error: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    if all(results):
        print("✅ All checks passed! Platform is ready to use.")
        print("\n🎯 Quick Start (No API Key):")
        print("  python -m src.main run examples/sample_prd.md --backend interactive")
        print("\n📋 Next steps:")
        print("  1. python -m src.main config-info")
        print("  2. python -m src.main analyze examples/sample_prd.md")
        print("  3. python -m src.main run examples/sample_prd.md --backend interactive")
        print("\n📖 Documentation:")
        print("  - QUICKSTART.md - Quick start guide")
        print("  - CLAUDE_CODE_USAGE.md - No API key usage guide")
        print("  - README.md - Full documentation")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
