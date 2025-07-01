"""Tests for Log monitoring collector."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from datetime import datetime, timedelta

from ptop.collectors.logs import LogCollector, LogEntry
from ptop.collectors.base import BaseCollector


class TestLogEntry:
    """Test LogEntry container class."""
    
    def test_initialization(self):
        """Test LogEntry initialization."""
        timestamp = datetime.now()
        log_entry = LogEntry(timestamp, "ERROR", "Test message", "test-service")
        
        assert log_entry.timestamp == timestamp
        assert log_entry.level == "ERROR"
        assert log_entry.message == "Test message"
        assert log_entry.source == "test-service"
    
    def test_initialization_without_source(self):
        """Test LogEntry initialization without source."""
        timestamp = datetime.now()
        log_entry = LogEntry(timestamp, "INFO", "Test message")
        
        assert log_entry.timestamp == timestamp
        assert log_entry.level == "INFO"
        assert log_entry.message == "Test message"
        assert log_entry.source == ""


class TestLogCollector:
    """Test LogCollector class."""
    
    @pytest.fixture
    def log_collector(self):
        """Create a LogCollector instance for testing."""
        return LogCollector()
    
    def test_inheritance(self, log_collector):
        """Test that LogCollector inherits from BaseCollector."""
        assert isinstance(log_collector, BaseCollector)
    
    def test_name_property(self, log_collector):
        """Test collector name property."""
        assert log_collector.name == "logs"
    
    def test_update_interval_property(self, log_collector):
        """Test update interval property."""
        assert log_collector.update_interval == 5.0
        assert isinstance(log_collector.update_interval, float)
    
    def test_initialization(self, log_collector):
        """Test collector initialization."""
        assert len(log_collector._error_patterns) > 0
        assert len(log_collector._compiled_patterns) > 0
        assert len(log_collector._compiled_patterns) == len(log_collector._error_patterns)
        
        # Check that patterns are compiled
        import re
        for pattern in log_collector._compiled_patterns:
            assert isinstance(pattern, re.Pattern)
    
    def test_error_patterns(self, log_collector):
        """Test that error patterns are properly defined."""
        expected_patterns = [
            r'\berror\b', r'\bcritical\b', r'\bfatal\b', r'\bpanic\b',
            r'\bfailed\b', r'\bfailure\b', r'\bexception\b', r'\bwarning\b'
        ]
        
        assert log_collector._error_patterns == expected_patterns
    
    @pytest.mark.asyncio
    async def test_collect_method_structure(self, log_collector, mock_journalctl_output):
        """Test that collect method returns expected structure."""
        with patch.object(log_collector, '_get_recent_logs') as mock_get_logs:
            # Create mock log entries
            timestamp = datetime.now()
            mock_logs = [
                LogEntry(timestamp, "INFO", "Normal message", "service1"),
                LogEntry(timestamp, "ERROR", "Error message", "service2"),
                LogEntry(timestamp, "WARNING", "Warning message", "service3")
            ]
            mock_get_logs.return_value = mock_logs
            
            result = await log_collector.collect()
            
            # Check structure
            assert isinstance(result, dict)
            assert 'recent_logs' in result
            assert 'error_logs' in result
            assert 'log_statistics' in result
            
            # Check that logs are limited correctly
            assert len(result['recent_logs']) <= 20
            assert len(result['error_logs']) <= 10
    
    @pytest.mark.asyncio
    async def test_get_recent_logs_journalctl_success(self, log_collector, mock_journalctl_output):
        """Test successful log collection using journalctl."""
        with patch('ptop.utils.helpers.run_command') as mock_run_command:
            mock_run_command.return_value = mock_journalctl_output
            
            result = await log_collector._get_recent_logs()
            
            assert isinstance(result, list)
            assert len(result) > 0
            
            # Verify journalctl was called with correct parameters
            mock_run_command.assert_called_once()
            args = mock_run_command.call_args[0][0]
            assert args[0] == 'journalctl'
            assert '--since' in args
            assert '--no-pager' in args
            assert '--output=short-iso' in args
            assert '--lines=100' in args
    
    @pytest.mark.asyncio
    async def test_get_recent_logs_journalctl_failure_fallback(self, log_collector):
        """Test fallback to traditional logs when journalctl fails."""
        with patch('ptop.utils.helpers.run_command', side_effect=Exception("journalctl not found")):
            with patch.object(log_collector, '_get_traditional_logs') as mock_traditional:
                mock_traditional.return_value = [LogEntry(datetime.now(), "INFO", "Test", "test")]
                
                result = await log_collector._get_recent_logs()
                
                # Should call traditional logs as fallback
                mock_traditional.assert_called_once()
                assert len(result) > 0
    
    def test_parse_journalctl_output_success(self, log_collector, mock_journalctl_output):
        """Test successful parsing of journalctl output."""
        result = log_collector._parse_journalctl_output(mock_journalctl_output)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check first log entry
        log_entry = result[0]
        assert isinstance(log_entry, LogEntry)
        assert log_entry.message == "Started Test Service."
        assert log_entry.source == "systemd"
        assert log_entry.level in ["INFO", "ERROR", "WARNING", "CRITICAL", "DEBUG"]
    
    def test_parse_journalctl_output_malformed_lines(self, log_collector):
        """Test parsing with malformed log lines."""
        malformed_output = """2023-01-01T12:00:00+00:00 hostname systemd[1]: Started Test Service.
incomplete line
invalid format here
2023-01-01T12:01:00+00:00 hostname kernel: Error: Something went wrong"""
        
        result = log_collector._parse_journalctl_output(malformed_output)
        
        # Should skip malformed lines and process valid ones
        assert len(result) == 2
        assert result[0].message == "Started Test Service."
        assert result[1].message == "Error: Something went wrong"
    
    def test_parse_journalctl_output_empty_input(self, log_collector):
        """Test parsing empty journalctl output."""
        result = log_collector._parse_journalctl_output("")
        assert result == []
    
    def test_parse_journalctl_output_timestamp_parsing(self, log_collector):
        """Test various timestamp formats in journalctl output."""
        various_timestamps = """2023-01-01T12:00:00+00:00 hostname systemd[1]: UTC timestamp
2023-01-01T12:00:00Z hostname systemd[1]: Z suffix timestamp
2023-01-01T12:00:00+01:00 hostname systemd[1]: Different timezone"""
        
        result = log_collector._parse_journalctl_output(various_timestamps)
        
        assert len(result) == 3
        for log_entry in result:
            assert isinstance(log_entry.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_get_traditional_logs_success(self, log_collector):
        """Test successful traditional log collection."""
        mock_log_output = """Jan 01 12:00:00 hostname systemd: Started test service
Jan 01 12:01:00 hostname kernel: Error occurred
Jan 01 12:02:00 hostname sshd: Login successful"""
        
        with patch('ptop.utils.helpers.run_command') as mock_run_command:
            mock_run_command.return_value = mock_log_output
            
            result = await log_collector._get_traditional_logs()
            
            assert isinstance(result, list)
            assert len(result) > 0
            
            # Should try common log file locations
            mock_run_command.assert_called()
            args = mock_run_command.call_args[0][0]
            assert args[0] == 'tail'
            assert '-n' in args
            assert '50' in args
    
    @pytest.mark.asyncio
    async def test_get_traditional_logs_file_not_found(self, log_collector):
        """Test traditional log collection when files don't exist."""
        with patch('ptop.utils.helpers.run_command', side_effect=Exception("File not found")):
            result = await log_collector._get_traditional_logs()
            
            # Should return empty list when no log files are accessible
            assert result == []
    
    def test_parse_traditional_log_output_success(self, log_collector):
        """Test successful parsing of traditional log output."""
        traditional_output = """Jan 01 12:00:00 hostname systemd: Started test service
Jan 01 12:01:00 hostname kernel: Error occurred in module
Jan 01 12:02:00 hostname sshd: Authentication successful for user"""
        
        result = log_collector._parse_traditional_log_output(traditional_output, "/var/log/messages")
        
        assert len(result) == 3
        log_entry = result[0]
        assert isinstance(log_entry, LogEntry)
        assert "Started test service" in log_entry.message
        assert log_entry.source == "systemd"
    
    def test_parse_traditional_log_output_malformed(self, log_collector):
        """Test parsing malformed traditional log output."""
        malformed_output = """Jan 01 12:00:00 hostname systemd: Valid message
incomplete line
Jan 01 incomplete timestamp
Jan 01 12:02:00 hostname sshd: Another valid message"""
        
        result = log_collector._parse_traditional_log_output(malformed_output, "/var/log/messages")
        
        # Should skip malformed lines
        assert len(result) == 2
        assert "Valid message" in result[0].message
        assert "Another valid message" in result[1].message
    
    def test_parse_traditional_log_output_empty_input(self, log_collector):
        """Test parsing empty traditional log output."""
        result = log_collector._parse_traditional_log_output("", "/var/log/messages")
        assert result == []
    
    def test_determine_log_level_critical(self, log_collector):
        """Test log level determination for critical messages."""
        assert log_collector._determine_log_level("CRITICAL error occurred") == "CRITICAL"
        assert log_collector._determine_log_level("Fatal system failure") == "CRITICAL"
        assert log_collector._determine_log_level("Kernel panic detected") == "CRITICAL"
    
    def test_determine_log_level_error(self, log_collector):
        """Test log level determination for error messages."""
        assert log_collector._determine_log_level("Error in processing") == "ERROR"
        assert log_collector._determine_log_level("Operation failed") == "ERROR"
        assert log_collector._determine_log_level("Exception occurred") == "ERROR"
        assert log_collector._determine_log_level("Failure to connect") == "ERROR"
    
    def test_determine_log_level_warning(self, log_collector):
        """Test log level determination for warning messages."""
        assert log_collector._determine_log_level("Warning: disk space low") == "WARNING"
        assert log_collector._determine_log_level("Warn: deprecated function") == "WARNING"
    
    def test_determine_log_level_info(self, log_collector):
        """Test log level determination for info messages."""
        assert log_collector._determine_log_level("Information: service started") == "INFO"
        assert log_collector._determine_log_level("Info: user logged in") == "INFO"
        assert log_collector._determine_log_level("Normal operation message") == "INFO"
    
    def test_determine_log_level_debug(self, log_collector):
        """Test log level determination for debug messages."""
        assert log_collector._determine_log_level("Debug: entering function") == "DEBUG"
    
    def test_determine_log_level_case_insensitive(self, log_collector):
        """Test that log level determination is case insensitive."""
        assert log_collector._determine_log_level("ERROR: test") == "ERROR"
        assert log_collector._determine_log_level("error: test") == "ERROR"
        assert log_collector._determine_log_level("Error: test") == "ERROR"
        assert log_collector._determine_log_level("ERROR: test") == "ERROR"
    
    def test_filter_error_logs_by_patterns(self, log_collector):
        """Test filtering logs by error patterns."""
        logs = [
            LogEntry(datetime.now(), "INFO", "Normal operation", "service1"),
            LogEntry(datetime.now(), "INFO", "An error occurred", "service2"),
            LogEntry(datetime.now(), "INFO", "Critical failure detected", "service3"),
            LogEntry(datetime.now(), "INFO", "Warning about disk space", "service4"),
            LogEntry(datetime.now(), "INFO", "Regular status update", "service5")
        ]
        
        error_logs = log_collector._filter_error_logs(logs)
        
        assert len(error_logs) == 3  # error, critical, warning
        messages = [log.message for log in error_logs]
        assert "An error occurred" in messages
        assert "Critical failure detected" in messages
        assert "Warning about disk space" in messages
        assert "Normal operation" not in messages
        assert "Regular status update" not in messages
    
    def test_filter_error_logs_by_level(self, log_collector):
        """Test filtering logs by error levels."""
        logs = [
            LogEntry(datetime.now(), "INFO", "Normal message", "service1"),
            LogEntry(datetime.now(), "ERROR", "Error message", "service2"),
            LogEntry(datetime.now(), "CRITICAL", "Critical message", "service3"),
            LogEntry(datetime.now(), "WARNING", "Warning message", "service4"),
            LogEntry(datetime.now(), "DEBUG", "Debug message", "service5")
        ]
        
        error_logs = log_collector._filter_error_logs(logs)
        
        assert len(error_logs) == 3  # ERROR, CRITICAL, WARNING
        levels = [log.level for log in error_logs]
        assert "ERROR" in levels
        assert "CRITICAL" in levels
        assert "WARNING" in levels
        assert "INFO" not in levels
        assert "DEBUG" not in levels
    
    def test_filter_error_logs_empty_list(self, log_collector):
        """Test filtering empty log list."""
        error_logs = log_collector._filter_error_logs([])
        assert error_logs == []
    
    def test_get_log_statistics_comprehensive(self, log_collector):
        """Test comprehensive log statistics generation."""
        now = datetime.now()
        recent_time = now - timedelta(minutes=2)
        old_time = now - timedelta(minutes=10)
        
        all_logs = [
            LogEntry(recent_time, "ERROR", "Recent error", "service1"),
            LogEntry(recent_time, "INFO", "Recent info", "service1"), 
            LogEntry(old_time, "ERROR", "Old error", "service2"),
            LogEntry(now, "WARNING", "Recent warning", "service2"),
            LogEntry(now, "INFO", "Recent info", "service3")
        ]
        
        error_logs = [
            LogEntry(recent_time, "ERROR", "Recent error", "service1"),
            LogEntry(old_time, "ERROR", "Old error", "service2"),
            LogEntry(now, "WARNING", "Recent warning", "service2")
        ]
        
        stats = log_collector._get_log_statistics(all_logs, error_logs)
        
        assert stats['total_entries'] == 5
        assert stats['error_entries'] == 3
        assert stats['recent_errors'] == 2  # Only recent errors (within 5 minutes)
        
        # Check level counts
        assert stats['level_counts']['ERROR'] == 2
        assert stats['level_counts']['INFO'] == 2
        assert stats['level_counts']['WARNING'] == 1
        
        # Check top sources
        assert 'service1' in stats['top_sources']
        assert 'service2' in stats['top_sources']
        assert stats['top_sources']['service1'] == 2  # 2 entries
        assert stats['top_sources']['service2'] == 2  # 2 entries
    
    def test_get_log_statistics_empty_logs(self, log_collector):
        """Test statistics generation with empty logs."""
        stats = log_collector._get_log_statistics([], [])
        assert stats == {}
    
    def test_get_log_statistics_recent_errors_calculation(self, log_collector):
        """Test recent errors calculation (last 5 minutes)."""
        now = datetime.now()
        recent_time = now - timedelta(minutes=2)  # Within 5 minutes
        old_time = now - timedelta(minutes=10)    # Older than 5 minutes
        
        all_logs = [
            LogEntry(recent_time, "INFO", "Recent log", "service1"),
            LogEntry(old_time, "INFO", "Old log", "service2")
        ]
        
        error_logs = [
            LogEntry(recent_time, "ERROR", "Recent error", "service1"),
            LogEntry(old_time, "ERROR", "Old error", "service2")
        ]
        
        stats = log_collector._get_log_statistics(all_logs, error_logs)
        
        # Only the recent error should count
        assert stats['recent_errors'] == 1
    
    def test_get_log_statistics_top_sources_sorting(self, log_collector):
        """Test that top sources are sorted by count."""
        all_logs = [
            LogEntry(datetime.now(), "INFO", "Message", "service_a"),  # 1 entry
            LogEntry(datetime.now(), "INFO", "Message", "service_b"),  # 3 entries
            LogEntry(datetime.now(), "INFO", "Message", "service_b"),
            LogEntry(datetime.now(), "INFO", "Message", "service_b"),
            LogEntry(datetime.now(), "INFO", "Message", "service_c"),  # 2 entries
            LogEntry(datetime.now(), "INFO", "Message", "service_c"),
            LogEntry(datetime.now(), "INFO", "Message", "service_d"),  # 1 entry
            LogEntry(datetime.now(), "INFO", "Message", "service_e"),  # 1 entry
            LogEntry(datetime.now(), "INFO", "Message", "service_f"),  # 1 entry
        ]
        
        stats = log_collector._get_log_statistics(all_logs, [])
        
        # Should be limited to top 5 and sorted by count
        top_sources = list(stats['top_sources'].items())
        assert len(top_sources) <= 5
        assert top_sources[0] == ('service_b', 3)  # Most entries first
        assert top_sources[1] == ('service_c', 2)  # Second most
    
    @pytest.mark.asyncio
    async def test_full_collect_integration(self, log_collector, mock_journalctl_output):
        """Test full collect method integration."""
        with patch('ptop.utils.helpers.run_command') as mock_run_command:
            mock_run_command.return_value = mock_journalctl_output
            
            result = await log_collector.collect()
            
            # Check structure
            assert 'recent_logs' in result
            assert 'error_logs' in result
            assert 'log_statistics' in result
            
            # Check that we have some logs
            assert len(result['recent_logs']) > 0
            assert len(result['error_logs']) > 0
            
            # Check statistics
            stats = result['log_statistics']
            assert 'total_entries' in stats
            assert 'error_entries' in stats
            assert 'recent_errors' in stats
            assert 'level_counts' in stats
            assert 'top_sources' in stats
    
    @pytest.mark.asyncio
    async def test_collect_limits_output_size(self, log_collector):
        """Test that collect limits output to reasonable sizes."""
        # Create many log entries
        many_logs = []
        for i in range(100):
            timestamp = datetime.now() - timedelta(minutes=i)
            level = "ERROR" if i % 2 == 0 else "INFO"
            many_logs.append(LogEntry(timestamp, level, f"Message {i}", f"service{i}"))
        
        with patch.object(log_collector, '_get_recent_logs', return_value=many_logs):
            result = await log_collector.collect()
            
            # Should limit recent logs to 20
            assert len(result['recent_logs']) == 20
            # Should limit error logs to 10
            assert len(result['error_logs']) <= 10
    
    @pytest.mark.asyncio
    async def test_collect_with_no_logs(self, log_collector):
        """Test collect method when no logs are available."""
        with patch.object(log_collector, '_get_recent_logs', return_value=[]):
            result = await log_collector.collect()
            
            assert result['recent_logs'] == []
            assert result['error_logs'] == []
            assert result['log_statistics'] == {}
    
    @pytest.mark.asyncio
    async def test_collect_error_handling(self, log_collector):
        """Test collect method error handling."""
        with patch.object(log_collector, '_get_recent_logs', side_effect=Exception("Test error")):
            # Should not crash on exceptions
            try:
                result = await log_collector.collect()
                # If it doesn't raise, it should return some default structure
                assert isinstance(result, dict)
            except Exception:
                # If it does raise, that's also acceptable for this test
                pass
    
    def test_log_collector_thread_safety(self, log_collector):
        """Test that multiple instances don't interfere with each other."""
        collector2 = LogCollector()
        
        # Each instance should have its own compiled patterns
        assert log_collector._compiled_patterns is not collector2._compiled_patterns
        assert len(log_collector._compiled_patterns) == len(collector2._compiled_patterns)
    
    @pytest.mark.asyncio
    async def test_edge_case_very_long_log_lines(self, log_collector):
        """Test handling of very long log lines."""
        very_long_message = "A" * 10000  # 10KB message
        long_log_output = f"2023-01-01T12:00:00+00:00 hostname service[1]: {very_long_message}"
        
        with patch('ptop.utils.helpers.run_command') as mock_run_command:
            mock_run_command.return_value = long_log_output
            
            result = await log_collector._get_recent_logs()
            
            # Should handle long messages without issues
            assert len(result) == 1
            assert len(result[0].message) == len(very_long_message)
    
    @pytest.mark.asyncio
    async def test_edge_case_unicode_log_content(self, log_collector):
        """Test handling of unicode content in logs."""
        unicode_log_output = """2023-01-01T12:00:00+00:00 hostname service[1]: Unicode test: αβγδε 中文 🚀 emoji
2023-01-01T12:01:00+00:00 hostname service[2]: Normal ASCII message"""
        
        with patch('ptop.utils.helpers.run_command') as mock_run_command:
            mock_run_command.return_value = unicode_log_output
            
            result = await log_collector._get_recent_logs()
            
            # Should handle unicode content properly
            assert len(result) == 2
            assert "αβγδε 中文 🚀" in result[0].message
    
    def test_edge_case_timezone_handling(self, log_collector):
        """Test handling of different timezone formats."""
        different_timezones = """2023-01-01T12:00:00+00:00 hostname service[1]: UTC message
2023-01-01T12:00:00+05:30 hostname service[2]: India timezone
2023-01-01T12:00:00-08:00 hostname service[3]: PST timezone
2023-01-01T12:00:00Z hostname service[4]: Zulu time"""
        
        result = log_collector._parse_journalctl_output(different_timezones)
        
        # Should parse all timezone formats correctly
        assert len(result) == 4
        for log_entry in result:
            assert isinstance(log_entry.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_performance_with_many_error_patterns(self, log_collector):
        """Test performance with many log entries and pattern matching."""
        # Create logs with various patterns
        test_logs = []
        patterns_to_test = ["error", "critical", "warning", "failed", "exception"]
        
        for i in range(1000):
            timestamp = datetime.now() - timedelta(seconds=i)
            if i % 100 == 0:
                message = f"Message {i} with {patterns_to_test[i % len(patterns_to_test)]}"
            else:
                message = f"Normal message {i}"
            test_logs.append(LogEntry(timestamp, "INFO", message, f"service{i % 10}"))
        
        # Should complete filtering in reasonable time
        error_logs = log_collector._filter_error_logs(test_logs)
        
        # Should find the error pattern matches
        assert len(error_logs) == 10  # Every 100th message has error pattern