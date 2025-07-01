"""Shared pytest fixtures and configuration."""

import pytest
from unittest.mock import patch, mock_open
from pathlib import Path
import tempfile
import json


@pytest.fixture
def mock_proc_stat():
    """Mock /proc/stat content."""
    return """cpu  123456 0 234567 890123 4567 0 1234 0 0 0
cpu0 61728 0 117283 445061 2283 0 617 0 0 0
cpu1 61728 0 117284 445062 2284 0 617 0 0 0"""


@pytest.fixture
def mock_proc_meminfo():
    """Mock /proc/meminfo content."""
    return """MemTotal:       16384000 kB
MemFree:         8192000 kB
MemAvailable:   12288000 kB
Buffers:          512000 kB
Cached:          2048000 kB
SwapTotal:       4194304 kB
SwapFree:        4194304 kB
SwapCached:            0 kB
Active:          4096000 kB
Inactive:        2048000 kB
Dirty:             32768 kB
Writeback:             0 kB
Mapped:           524288 kB
Shmem:            262144 kB
Slab:             131072 kB
SReclaimable:      65536 kB
SUnreclaim:        65536 kB"""


@pytest.fixture
def mock_proc_cpuinfo():
    """Mock /proc/cpuinfo content."""
    return """processor	: 0
vendor_id	: GenuineIntel
cpu family	: 6
model		: 142
model name	: Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz
stepping	: 10
microcode	: 0xf0
cpu MHz		: 2400.000
cache size	: 8192 KB

processor	: 1
vendor_id	: GenuineIntel
cpu family	: 6
model		: 142
model name	: Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz
stepping	: 10
microcode	: 0xf0
cpu MHz		: 2401.000
cache size	: 8192 KB"""


@pytest.fixture
def mock_proc_loadavg():
    """Mock /proc/loadavg content."""
    return "1.23 2.34 3.45 2/456 12345"


@pytest.fixture
def mock_proc_diskstats():
    """Mock /proc/diskstats content."""
    return """   8       0 sda 123456 789 2345678 9012 345678 901 4567890 2345 0 6789 11357
   8       1 sda1 98765 432 1876543 6543 210987 654 3210987 1234 0 4321 7777
   8      16 sdb 54321 210 987654 3210 123456 321 1234567 789 0 1000 4000"""


@pytest.fixture
def mock_proc_mounts():
    """Mock /proc/mounts content."""
    return """/dev/sda1 / ext4 rw,relatime,errors=remount-ro 0 0
/dev/sda2 /home ext4 rw,relatime 0 0
tmpfs /tmp tmpfs rw,nosuid,nodev,size=2097152k 0 0
proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0"""


@pytest.fixture
def mock_journalctl_output():
    """Mock journalctl output."""
    return """2023-01-01T12:00:00+00:00 hostname systemd[1]: Started Test Service.
2023-01-01T12:01:00+00:00 hostname kernel: Error: Something went wrong
2023-01-01T12:02:00+00:00 hostname sshd[1234]: Failed login attempt
2023-01-01T12:03:00+00:00 hostname test-app[5678]: Critical error occurred"""


@pytest.fixture
def temp_config_file():
    """Create a temporary configuration file."""
    config_data = {
        "cpu_update_interval": 2.0,
        "memory_update_interval": 1.5,
        "show_cpu_per_core": False,
        "cpu_warning_threshold": 80.0
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    temp_path.unlink()


@pytest.fixture
def mock_process_list():
    """Mock process list."""
    return [1, 2, 123, 456, 789, 1000]


@pytest.fixture
def mock_process_stat():
    """Mock /proc/[pid]/stat content."""
    return "123 (test-process) S 1 123 123 0 -1 4194304 123 0 0 0 10 5 0 0 20 0 1 0 12345 1234567 100 18446744073709551615 0 0 0 0 0 0 0 0 0 0 0 0 17 0 0 0 0 0 0 0 0 0 0 0 0 0 0"


@pytest.fixture
def mock_process_status():
    """Mock /proc/[pid]/status content."""
    return """Name:	test-process
State:	S (sleeping)
Tgid:	123
Ngid:	0
Pid:	123
PPid:	1
TracerPid:	0
Uid:	1000	1000	1000	1000
Gid:	1000	1000	1000	1000
FDSize:	256
Groups:	1000
VmPeak:	  123456 kB
VmSize:	  123456 kB
VmLck:	       0 kB
VmPin:	       0 kB
VmHWM:	   12345 kB
VmRSS:	   12345 kB
RssAnon:	    1234 kB
RssFile:	   11111 kB
RssShmem:	      0 kB
VmData:	   23456 kB
VmStk:	     132 kB
VmExe:	    1024 kB
VmLib:	    5678 kB
VmPTE:	      80 kB
VmSwap:	       0 kB
Threads:	1"""


@pytest.fixture
def mock_statvfs():
    """Mock os.statvfs result."""
    class MockStatvfs:
        f_blocks = 1000000
        f_bfree = 500000
        f_bavail = 450000
        f_frsize = 4096
    
    return MockStatvfs()


@pytest.fixture
def mock_read_proc_file(mocker):
    """Mock the read_proc_file helper function."""
    return mocker.patch('ptop.utils.helpers.read_proc_file')


@pytest.fixture
def mock_run_command(mocker):
    """Mock the run_command helper function."""
    return mocker.patch('ptop.utils.helpers.run_command')