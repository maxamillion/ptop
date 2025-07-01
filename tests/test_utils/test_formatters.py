"""Tests for formatting utilities."""

import pytest
from ptop.utils.formatters import (
    format_bytes,
    format_percentage,
    format_frequency,
    format_uptime,
    format_load_average
)


class TestFormatBytes:
    """Test format_bytes function."""
    
    @pytest.mark.parametrize("bytes_value,expected", [
        (0, "0 B"),
        (1, "1 B"),
        (1023, "1023 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1048576, "1.0 MB"),
        (1572864, "1.5 MB"),
        (1073741824, "1.0 GB"),
        (1610612736, "1.5 GB"),
        (1099511627776, "1.0 TB"),
        (1125899906842624, "1.0 PB"),
        (1152921504606846976, "1.0 EB"),  # Test beyond PB
        (None, "N/A"),
    ])
    def test_format_bytes_various_sizes(self, bytes_value, expected):
        """Test formatting of various byte values."""
        assert format_bytes(bytes_value) == expected
    
    def test_format_bytes_float_values(self):
        """Test formatting with float values."""
        assert format_bytes(1536.7) == "1.5 KB"
        assert format_bytes(1073741824.5) == "1.0 GB"
    
    def test_format_bytes_large_numbers(self):
        """Test very large numbers."""
        # Test petabytes and beyond
        result = format_bytes(1125899906842624 * 1024)  # 1024 PB
        assert "EB" in result or "PB" in result


class TestFormatPercentage:
    """Test format_percentage function."""
    
    @pytest.mark.parametrize("value,precision,expected", [
        (0, 1, "0.0%"),
        (50.0, 1, "50.0%"),
        (100.0, 1, "100.0%"),
        (99.95, 1, "100.0%"),
        (99.94, 1, "99.9%"),
        (50.123, 2, "50.12%"),
        (50.126, 2, "50.13%"),
        (None, 1, "N/A"),
        (0, 0, "0%"),
        (150.5, 1, "150.5%"),  # Over 100%
    ])
    def test_format_percentage_various_values(self, value, precision, expected):
        """Test formatting of various percentage values."""
        assert format_percentage(value, precision) == expected
    
    def test_format_percentage_default_precision(self):
        """Test default precision (1)."""
        assert format_percentage(50.123) == "50.1%"


class TestFormatFrequency:
    """Test format_frequency function."""
    
    @pytest.mark.parametrize("hz_value,expected", [
        (0, "0 Hz"),
        (500, "500 Hz"),
        (999, "999 Hz"),
        (1000, "1 KHz"),
        (1500, "2 KHz"),  # Rounded
        (999999, "1000 KHz"),
        (1000000, "1 MHz"),
        (1500000, "2 MHz"),  # Rounded
        (2400000000, "2.4 GHz"),
        (2400500000, "2.4 GHz"),
        (None, "N/A"),
    ])
    def test_format_frequency_various_values(self, hz_value, expected):
        """Test formatting of various frequency values."""
        assert format_frequency(hz_value) == expected
    
    def test_format_frequency_float_values(self):
        """Test formatting with float values."""
        assert format_frequency(2400.5e6) == "2.4 GHz"
        assert format_frequency(1500.7e3) == "2 MHz"


class TestFormatUptime:
    """Test format_uptime function."""
    
    @pytest.mark.parametrize("seconds,expected", [
        (0, "0m"),
        (30, "0m"),
        (60, "1m"),
        (3600, "1h 0m"),
        (3660, "1h 1m"),
        (86400, "1d 0h 0m"),
        (90061, "1d 1h 1m"),
        (172800, "2d 0h 0m"),
        (259261, "3d 0h 1m"),  # 3 days and 1 minute
        (None, "N/A"),
    ])
    def test_format_uptime_various_values(self, seconds, expected):
        """Test formatting of various uptime values."""
        assert format_uptime(seconds) == expected
    
    def test_format_uptime_float_values(self):
        """Test formatting with float values."""
        assert format_uptime(3660.5) == "1h 1m"
        assert format_uptime(90061.9) == "1d 1h 1m"


class TestFormatLoadAverage:
    """Test format_load_average function."""
    
    @pytest.mark.parametrize("load_avg,expected", [
        (0.0, "0.00"),
        (1.0, "1.00"),
        (1.234, "1.23"),
        (1.235, "1.24"),  # Rounded up
        (10.999, "11.00"),
        (None, "N/A"),
    ])
    def test_format_load_average_various_values(self, load_avg, expected):
        """Test formatting of various load average values."""
        assert format_load_average(load_avg) == expected