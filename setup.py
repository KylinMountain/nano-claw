"""
Nano Agent - A lightweight AI agent framework
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="nano-claw",
    version="0.1.0",
    author="Nano Agent Contributors",
    author_email="",
    description="A lightweight AI agent framework in ~5K lines of code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/nano-claw",
    packages=find_packages(exclude=["tests", "examples", "docs"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "openai>=1.0.0",
        "anthropic>=0.18.0",
        "google-generativeai>=0.3.0",
        "pydantic>=2.0.0",
        "pyyaml>=6.0",
        "rich>=13.0.0",
        "prompt-toolkit>=3.0.0",
        "aiohttp>=3.9.0",
        "mcp>=0.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "all": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "nano-claw=nano_claw.main:main",
            "nano-claw-cli=nano_claw.cli:main",
        ],
    },
    keywords=[
        "ai",
        "agent",
        "llm",
        "mcp",
        "openai",
        "anthropic",
        "google",
        "gemini",
        "assistant",
        "chatbot",
        "automation",
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/nano-claw/issues",
        "Source": "https://github.com/yourusername/nano-claw",
        "Documentation": "https://github.com/yourusername/nano-claw/tree/main/docs",
    },
)
