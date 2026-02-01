"""Setup script for agentic swarm platform."""

from setuptools import setup, find_packages

setup(
    name="agentic-swarm-platform",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "anthropic>=0.40.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
        "structlog>=24.0.0",
        "tenacity>=8.0.0",
        "aiofiles>=23.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "agentic-swarm=src.main:cli",
        ],
    },
)
