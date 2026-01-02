# 🌙 Gloom

> High-performance CLI for Google Cloud Context & ADC Switching

[![CI](https://github.com/hilmanmustofaa/gloom/actions/workflows/ci.yml/badge.svg)](https://github.com/hilmanmustofaa/gloom/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Gloom** manages gcloud configurations and Application Default Credentials (ADC) via symlink manipulation, enabling **sub-100ms context switching** between Google Cloud projects.

## ✨ Features

- ⚡ **Instant Switching** - Symlink-based ADC switching in <100ms (vs 5-15s for `gcloud auth`)
- 🔒 **Secure** - Cached credentials stored with 0600 permissions
- 🔄 **Atomic Operations** - Safe symlink switching prevents partial states
- 📦 **Zero Re-authentication** - Cache ADC per-project, switch without re-login
- 🐚 **Shell Integration** - Prompt hooks for bash, zsh, fish, PowerShell

## 🚀 Quick Start

### Installation

```bash
# With pip
pip install gloom

# With uv (recommended)
uv pip install gloom

# From source
git clone https://github.com/hilmanmustofaa/gloom.git
cd gloom
uv sync --dev
```

### Basic Usage

```bash
# Cache your current ADC as a named context
gcloud auth application-default login  # authenticate first
gloom cache add production

# Switch to a different project, authenticate, and cache
gcloud auth application-default login --project other-project
gloom cache add staging

# List cached contexts
gloom list

# Switch between contexts instantly
gloom switch production
gloom switch staging

# Show current context
gloom current
```

## 📖 Commands

### Core Commands

| Command               | Description                  |
| --------------------- | ---------------------------- |
| `gloom list`          | List all cached ADC contexts |
| `gloom switch <name>` | Switch to a cached context   |
| `gloom current`       | Show the current ADC context |

### Cache Management

| Command                            | Description                        |
| ---------------------------------- | ---------------------------------- |
| `gloom cache add <name>`           | Cache current ADC as named context |
| `gloom cache add <name> -s <path>` | Cache ADC from specific file       |
| `gloom cache remove <name>`        | Remove a cached context            |
| `gloom cache list`                 | List cached contexts (alias)       |

### gcloud Configuration

| Command                        | Description                      |
| ------------------------------ | -------------------------------- |
| `gloom config list`            | List gcloud named configurations |
| `gloom config activate <name>` | Activate a gcloud configuration  |

## 🔧 How It Works

Instead of re-authenticating with `gcloud auth application-default login` each time you switch projects, Gloom:

1. **Caches** your ADC file to `~/.gloom/cache/<project>/adc.json`
2. **Symlinks** `~/.config/gcloud/application_default_credentials.json` to the cached file
3. **Switches** contexts by atomically updating the symlink

```
~/.gloom/cache/
├── production/adc.json
├── staging/adc.json
└── development/adc.json

~/.config/gcloud/application_default_credentials.json
  → symlink to → ~/.gloom/cache/production/adc.json
```

## 🔐 Security

- Cached credentials are stored with **0600** permissions (owner read/write only)
- Cache directory has **0700** permissions
- Pre-commit hooks prevent accidental secret commits
- Audit logging tracks all context switches

## 🛠️ Development

```bash
# Clone and setup
git clone https://github.com/hilmanmustofaa/gloom.git
cd gloom
uv sync --dev

# Install pre-commit hooks
pre-commit install

# Run tests
uv run pytest

# Run linting
uv run ruff check .
uv run ruff format --check .

# Run type checking
uv run mypy src/gloom/
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
