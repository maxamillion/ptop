# Unit Testing Plan for 100% Code Coverage

## Overview
This plan outlines a comprehensive testing strategy to achieve 100% code coverage for the ptop system monitoring tool using pytest.

## Test Configuration

### Additional Dependencies Required
```bash
# Add to pyproject.toml [dependency-groups.dev]
uv add --dev pytest-cov pytest-mock pytest-textual pytest-asyncio
```

### Coverage Configuration
Create `pytest.ini`:
```ini
[tool:pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --cov=src/ptop
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=100
    --strict-warnings
```

## Test Structure and Coverage Plan

### Phase 1: Utility Functions (Easy Wins)
**Target**: `src/ptop/utils/` - 100% coverage in 1-2 hours

#### `test_utils/test_formatters.py`
- `format_bytes()`: Test all units (B, KB, MB, GB, TB, PB), edge cases (None, 0, large numbers)
- `format_percentage()`: Test precision, None values, edge cases (0, 100, >100)
- `format_frequency()`: Test Hz, KHz, MHz, GHz conversions, None values
- `format_uptime()`: Test days, hours, minutes combinations, edge cases
- `format_load_average()`: Test precision, None values

#### `test_utils/test_helpers.py`
- `read_proc_file()`: Mock file operations, test permissions, non-existent files
- `parse_proc_stat_line()`: Test valid/invalid stat lines, different field counts
- `calculate_cpu_percentage()`: Test with various CPU time deltas, edge cases
- `parse_meminfo()`: Test real meminfo format, malformed lines
- `get_process_list()`: Mock `/proc` directory, test permissions
- `run_command()`: Mock subprocess calls, test failures, timeouts

### Phase 2: Configuration System
**Target**: `src/ptop/config/` - 100% coverage in 2-3 hours

#### `test_config/test_settings.py`
- `PtopSettings` model validation: Test all field types, defaults
- `load_from_file()`: Test file loading hierarchy, missing files, malformed JSON
- `save_to_file()`: Test file creation, directory creation, permissions
- Configuration precedence testing
- Invalid configuration handling

### Phase 3: Base Classes and Abstract Components
**Target**: `src/ptop/collectors/base.py`, `src/ptop/widgets/base.py` - 100% coverage in 1 hour

#### `test_collectors/test_base.py`
- Test abstract methods raise NotImplementedError
- Test inheritance patterns

#### `test_widgets/test_base.py`
- Test `BaseMetricWidget.update_data()`
- Test reactive data updates
- Test compose method

### Phase 4: Collectors (Complex System Integration)
**Target**: All collectors - 100% coverage in 8-10 hours

#### `test_collectors/test_cpu.py`
Mock Strategy: Mock all `/proc` file reads
- `collect()`: Test complete data collection cycle
- `_get_cpu_info()`: Mock `/proc/cpuinfo`, test parsing
- `_get_cpu_usage()`: Mock `/proc/stat`, test CPU percentage calculations
- `_get_load_averages()`: Mock `/proc/loadavg`
- `_get_cpu_frequencies()`: Test frequency parsing, missing data
- Edge cases: Permission denied, malformed files, missing files
- State persistence: Test previous CPU times storage

#### `test_collectors/test_memory.py`
- `collect()`: Test complete memory collection
- `_get_memory_info()`: Mock `/proc/meminfo`, test all memory fields
- `_get_swap_info()`: Test swap parsing
- `_calculate_memory_metrics()`: Test percentage calculations, edge cases
- Error handling: Missing meminfo, permission issues

#### `test_collectors/test_process.py`
- `collect()`: Test process collection with mocked process list
- `_get_process_info()`: Mock individual process files, test parsing
- `_parse_stat()`: Test stat file parsing, CPU calculation
- `_parse_status()`: Test status file parsing
- `_get_process_summary()`: Test statistics calculation
- Edge cases: Processes disappearing, permission denied, malformed data
- Performance: Test with large process lists

#### `test_collectors/test_storage.py`
- `collect()`: Test filesystem and I/O collection
- `_get_filesystem_usage()`: Mock `/proc/mounts` and `os.statvfs`
- `_get_disk_io_stats()`: Mock `/proc/diskstats`, test I/O calculations
- Rate calculations: Test I/O rate computations over time
- Error handling: Permission issues, unmounted filesystems

#### `test_collectors/test_logs.py`
- `collect()`: Test log collection cycle
- `_get_recent_logs()`: Mock journalctl and fallback mechanisms
- `_parse_journalctl_output()`: Test journalctl parsing
- `_get_traditional_logs()`: Test syslog parsing
- `_filter_error_logs()`: Test pattern matching
- `_determine_log_level()`: Test level detection
- Command execution mocking for journalctl

### Phase 5: Widgets (UI Component Testing)
**Target**: All widgets - 100% coverage in 6-8 hours

#### `test_widgets/test_cpu_widget.py`
- `render()`: Test with various data states (empty, partial, complete)
- Progress bar rendering with different CPU percentages
- Color coding logic (green/yellow/red thresholds)
- Per-core display logic
- Load average formatting

#### `test_widgets/test_memory_widget.py`
- Memory usage display with different data combinations
- Swap memory handling (enabled/disabled)
- Progress bar calculations
- Buffer/cache display logic

#### `test_widgets/test_process_widget.py`
- Process table rendering with different process counts
- Sorting and filtering logic
- Summary statistics display
- Process data formatting

#### `test_widgets/test_storage_widget.py`
- Filesystem usage display
- I/O statistics rendering
- Progress bars for disk usage
- Multiple filesystem handling

#### `test_widgets/test_logs_widget.py`
- Log entry display
- Error highlighting
- Statistics display
- Source breakdown

### Phase 6: Main Application
**Target**: `src/ptop/app.py` - 100% coverage in 6-8 hours

#### `test_app/test_ptop_app.py`
- Application initialization
- Collector initialization in `_initialize_collectors()`
- Data collection startup in `_start_data_collection()`
- Widget update mechanism in `_update_widget()`
- Async task coordination
- Error handling in collection loops
- Action handlers (quit, refresh, help)
- CSS and layout composition

### Phase 7: CLI Entry Point
**Target**: `src/ptop/main.py` - 100% coverage in 2-3 hours

#### `test_main.py`
- CLI argument parsing
- Configuration loading with different options
- Application startup
- Error handling for invalid arguments
- Help and version display

## Mock Strategy and Test Utilities

### Core Mocking Patterns

#### System File Mocking
```python
# conftest.py
import pytest
from unittest.mock import patch, mock_open

@pytest.fixture
def mock_proc_stat():
    return """cpu  123456 0 234567 890123 4567 0 1234 0 0 0
cpu0 61728 0 117283 445061 2283 0 617 0 0 0
cpu1 61728 0 117284 445062 2284 0 617 0 0 0"""

@pytest.fixture
def mock_proc_meminfo():
    return """MemTotal:       16384000 kB
MemFree:         8192000 kB
MemAvailable:   12288000 kB
Buffers:          512000 kB
Cached:          2048000 kB"""
```

#### Async Testing Patterns
```python
@pytest.mark.asyncio
async def test_collector_async_method():
    collector = CPUCollector()
    with patch('ptop.utils.helpers.read_proc_file') as mock_read:
        mock_read.return_value = mock_data
        result = await collector.collect()
        assert result['cpu_count'] == 2
```

#### Textual Widget Testing
```python
from textual.testing import App

async def test_widget_rendering():
    app = App()
    widget = CPUWidget()
    widget.data = {'overall_cpu_usage': 50.0}
    panel = widget.render()
    assert "50.0%" in str(panel)
```

### Parametrized Testing for Edge Cases

```python
@pytest.mark.parametrize("bytes_value,expected", [
    (0, "0 B"),
    (1023, "1023 B"),
    (1024, "1.0 KB"),
    (1536, "1.5 KB"),
    (None, "N/A"),
])
def test_format_bytes(bytes_value, expected):
    assert format_bytes(bytes_value) == expected
```

## Testing Challenges and Solutions

### Challenge 1: System Dependencies
**Solution**: Mock all system calls, file reads, and subprocess execution

### Challenge 2: Async Coordination
**Solution**: Use pytest-asyncio, mock asyncio.create_task, test task coordination

### Challenge 3: Textual UI Testing
**Solution**: Test render methods directly, mock Textual app context when needed

### Challenge 4: Time-Dependent Calculations
**Solution**: Mock time functions, use fixed time deltas for rate calculations

### Challenge 5: Permission-Based Code Paths
**Solution**: Mock OSError/PermissionError exceptions to test fallback paths

## Execution Plan

### Week 1: Foundation (Phases 1-3)
- Set up testing infrastructure
- Implement utility and configuration tests
- Create base class tests and mock patterns

### Week 2: Core Logic (Phases 4-5)
- Implement collector tests with comprehensive mocking
- Create widget rendering tests
- Focus on edge cases and error conditions

### Week 3: Integration (Phases 6-7)
- Application-level testing
- CLI testing
- Integration test scenarios
- Coverage analysis and gap filling

### Continuous Monitoring
```bash
# Run coverage checks
uv run pytest --cov=src/ptop --cov-report=html

# Generate detailed coverage report
uv run coverage html
open htmlcov/index.html

# Check for uncovered lines
uv run coverage report --show-missing
```

## Success Metrics

1. **100% Line Coverage**: Every line of code executed in tests
2. **100% Branch Coverage**: Every conditional path tested
3. **Error Path Coverage**: All exception handling tested
4. **Edge Case Coverage**: Boundary conditions and invalid inputs tested
5. **Integration Coverage**: Component interaction patterns tested

## Estimated Timeline

- **Total Effort**: 25-30 hours
- **Timeline**: 3 weeks (8-10 hours/week)
- **Complexity Distribution**:
  - Easy (Utils/Config): 20%
  - Medium (Widgets/CLI): 30%
  - Hard (Collectors/App): 50%

This comprehensive plan ensures systematic coverage of all code paths while maintaining test quality and maintainability.