# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Setup
```bash
# Install dependencies and setup development environment
uv sync --dev

# Run the application
uv run python -m ptop.main

# Run with options
uv run python -m ptop.main --config /path/to/config.json --interval 2.0
```

### Code Quality and Testing
```bash
# Format code
uv run black src/

# Lint code
uv run ruff check src/

# Type checking
uv run mypy src/

# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/test_collectors/test_cpu.py

# Run tests with coverage
uv run pytest --cov=src/ptop
```

### Package Management
```bash
# Add new dependency
uv add package_name

# Add development dependency
uv add --dev package_name

# Install in editable mode
uv sync -e
```

## Architecture Overview

### Core Design Pattern
ptop follows a **collector-widget-application** architecture:

1. **Collectors** (`src/ptop/collectors/`): Asynchronous data gathering from system APIs
2. **Widgets** (`src/ptop/widgets/`): Textual UI components that render collected data
3. **Application** (`src/ptop/app.py`): Coordinates data flow between collectors and widgets

### Data Flow
```
System APIs (/proc, journalctl) → Collectors → Application → Widgets → Terminal UI
```

### Key Components

**BaseCollector** (`collectors/base.py`): Abstract base defining the collector interface
- `async collect() -> Dict[str, Any]`: Returns metrics data
- `update_interval: float`: Defines collection frequency  
- `name: str`: Collector identifier

**PtopApp** (`app.py`): Main Textual application that:
- Initializes all collectors in `_initialize_collectors()`
- Starts async collection loops in `_start_data_collection()`
- Updates widgets via `_update_widget()` using collector name + "-widget" ID pattern

**Widget Data Binding**: Widgets are updated by matching collector names to widget IDs:
- `cpu` collector → `#cpu-widget`
- `memory` collector → `#memory-widget`
- etc.

### Collector Implementation Pattern
Each collector inherits from `BaseCollector` and implements system-specific data gathering:
- **CPU**: Parses `/proc/stat`, `/proc/cpuinfo`, `/proc/loadavg`
- **Memory**: Reads `/proc/meminfo`, calculates usage percentages
- **Process**: Iterates `/proc/[pid]/` directories, tracks CPU deltas over time
- **Storage**: Combines `/proc/mounts`, `/proc/diskstats`, `os.statvfs()`
- **Logs**: Uses `journalctl` with fallback to traditional log files

### Widget Rendering
Widgets extend `BaseMetricWidget` and implement Rich Panel rendering:
- Data updates trigger `refresh()` via reactive `data` property
- `render()` method returns Rich Panel with formatted metrics
- Color-coded borders based on threshold values (green/yellow/red)

### Configuration System
- Pydantic-based settings in `config/settings.py`
- JSON configuration files with hierarchical loading
- Runtime overrides via CLI arguments

### Async Coordination
- Each collector runs in its own asyncio task with independent update intervals
- Application coordinates all collectors without blocking the UI event loop
- Error handling allows individual collector failures without crashing the app

## Development Notes

### Adding New Metrics
1. Create collector in `collectors/` inheriting from `BaseCollector`
2. Create widget in `widgets/` inheriting from `BaseMetricWidget`
3. Register both in `app.py` `_initialize_collectors()` and `compose()`
4. Follow the `{name}-widget` ID naming convention

### Textual Framework Integration
- Uses Textual's reactive system for data binding
- CSS styling defined inline within `PtopApp.CSS`
- Responsive layout with `Horizontal`/`Vertical` containers

### System API Patterns
- Robust error handling for permission denied scenarios
- Graceful degradation when system files unavailable
- Efficient parsing of `/proc` filesystem data structures