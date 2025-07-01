# ptop - Modern Python System Monitor

A modern, Python-based system monitoring tool designed for Linux systems administrators. Built with the Textual framework, ptop provides real-time system metrics in an intuitive terminal user interface.

## Features

- **Real-time monitoring** of system metrics
- **CPU monitoring** with per-core usage, load averages, and frequencies
- **Memory monitoring** including physical memory, swap, buffers, and cache
- **Process management** with detailed process information and sorting
- **Storage monitoring** with filesystem usage and disk I/O statistics
- **System log monitoring** with error detection and filtering
- **Modern terminal UI** built with Textual framework
- **Configurable refresh intervals** and thresholds
- **Low resource overhead** (<1% CPU, <50MB RAM)

## Requirements

- Python 3.10+
- Linux operating system
- Terminal with Unicode support

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd ptop

# Install with uv
uv sync
```

### Manual Installation

```bash
# Clone the repository
git clone <repository-url>
cd ptop

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

## Usage

### Basic Usage

```bash
# Run ptop with default settings
ptop

# Run with custom update interval
ptop --interval 2.0

# Run with custom configuration file
ptop --config /path/to/config.json
```

### Keyboard Shortcuts

- `q` - Quit the application
- `r` - Manually refresh all metrics
- `h` - Show help (not yet implemented)
- `Ctrl+C` - Force quit

## Configuration

ptop can be configured using a JSON configuration file. The application looks for configuration files in the following order:

1. Path specified with `--config` option
2. `~/.config/ptop/config.json`
3. `/etc/ptop/config.json`
4. `./config.json` (current directory)

### Configuration Options

```json
{
  "cpu_update_interval": 1.0,
  "memory_update_interval": 1.0,
  "storage_update_interval": 2.0,
  "process_update_interval": 2.0,
  "log_update_interval": 5.0,
  "show_cpu_per_core": true,
  "show_memory_swap": true,
  "show_process_tree": false,
  "process_count_limit": 50,
  "cpu_warning_threshold": 70.0,
  "cpu_critical_threshold": 90.0,
  "memory_warning_threshold": 80.0,
  "memory_critical_threshold": 95.0,
  "log_sources": ["/var/log/messages", "/var/log/syslog"],
  "error_patterns": ["error", "critical", "fatal", "panic"]
}
```

## Architecture

ptop is built with a modular architecture:

- **Collectors**: Gather system metrics from various sources (`/proc`, `journalctl`, etc.)
- **Widgets**: Display metrics using Rich/Textual components
- **Application**: Coordinates data collection and UI updates

### Key Components

- `CPUCollector`: Monitors CPU usage, load averages, and frequencies
- `MemoryCollector`: Tracks memory usage and swap statistics
- `ProcessCollector`: Manages process information and statistics
- `StorageCollector`: Monitors filesystem usage and disk I/O
- `LogCollector`: Analyzes system logs for errors and warnings

## Development

### Development Setup

```bash
# Install development dependencies
uv sync --dev

# Run code formatting
uv run black src/

# Run linting
uv run ruff check src/

# Run type checking
uv run mypy src/

# Run tests
uv run pytest
```

### Project Structure

```
ptop/
├── src/ptop/
│   ├── collectors/     # Metric collection modules
│   ├── widgets/        # UI display components
│   ├── config/         # Configuration management
│   ├── utils/          # Utility functions
│   ├── app.py          # Main application
│   └── main.py         # CLI entry point
├── tests/              # Test suite
├── docs/               # Documentation
└── pyproject.toml      # Project configuration
```

## Performance

ptop is designed to be lightweight and efficient:

- Memory usage: <50MB typical
- CPU overhead: <1% on modern systems
- Update intervals: Configurable (1-5 seconds default)
- Responsive UI: <100ms refresh lag

## Troubleshooting

### Permission Issues

Some metrics require elevated privileges:

```bash
# Run with sudo for full system access
sudo ptop
```

### Missing Dependencies

If you encounter import errors, ensure all dependencies are installed:

```bash
uv sync --dev
```

### Log Access Issues

For log monitoring, ensure the user has read access to system logs:

```bash
# Add user to systemd-journal group (for journalctl access)
sudo usermod -a -G systemd-journal $USER

# Or run with sudo for full log access
sudo ptop
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is open source. See LICENSE file for details.

## Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual) framework
- Inspired by htop, glances, and btop
- Uses [Rich](https://github.com/Textualize/rich) for terminal formatting
