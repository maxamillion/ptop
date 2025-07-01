"""Log monitoring collector."""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from .base import BaseCollector
from ..utils.helpers import run_command


class LogEntry:
    """Container for log entry information."""
    
    def __init__(self, timestamp: datetime, level: str, message: str, source: str = ""):
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.source = source


class LogCollector(BaseCollector):
    """Collector for system log monitoring."""
    
    def __init__(self) -> None:
        self._error_patterns = [
            r'\berror\b', r'\bcritical\b', r'\bfatal\b', r'\bpanic\b',
            r'\bfailed\b', r'\bfailure\b', r'\bexception\b', r'\bwarning\b'
        ]
        self._compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self._error_patterns]
    
    @property
    def name(self) -> str:
        return "logs"
    
    @property
    def update_interval(self) -> float:
        return 5.0
    
    async def collect(self) -> Dict[str, Any]:
        """Collect log metrics.
        
        Returns:
            Dictionary containing log metrics.
        """
        metrics = {}
        
        # Get recent system logs
        recent_logs = await self._get_recent_logs()
        
        # Filter for errors and warnings
        error_logs = self._filter_error_logs(recent_logs)
        
        # Get log statistics
        log_stats = self._get_log_statistics(recent_logs, error_logs)
        
        metrics.update({
            'recent_logs': recent_logs[-20:],  # Last 20 log entries
            'error_logs': error_logs[-10:],    # Last 10 error entries
            'log_statistics': log_stats
        })
        
        return metrics
    
    async def _get_recent_logs(self) -> List[LogEntry]:
        """Get recent system logs using journalctl."""
        logs = []
        
        try:
            # Try to get logs from journalctl (systemd systems)
            since_time = datetime.now() - timedelta(minutes=10)
            since_str = since_time.strftime('%Y-%m-%d %H:%M:%S')
            
            output = await run_command([
                'journalctl',
                '--since', since_str,
                '--no-pager',
                '--output=short-iso',
                '--lines=100'
            ])
            
            if output:
                logs.extend(self._parse_journalctl_output(output))
        except Exception:
            # Fallback to traditional log files if journalctl is not available
            logs.extend(await self._get_traditional_logs())
        
        return logs
    
    def _parse_journalctl_output(self, output: str) -> List[LogEntry]:
        """Parse journalctl output into LogEntry objects."""
        logs = []
        
        for line in output.split('\n'):
            if not line.strip():
                continue
            
            try:
                # Parse journalctl short-iso format
                # Format: 2023-01-01T12:00:00+00:00 hostname service[pid]: message
                parts = line.split(' ', 3)
                if len(parts) < 4:
                    continue
                
                timestamp_str = parts[0]
                hostname = parts[1]
                service_part = parts[2]
                message = parts[3]
                
                # Parse timestamp
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
                # Extract service name
                service_match = re.match(r'([^[]+)', service_part)
                source = service_match.group(1) if service_match else service_part
                
                # Determine log level from message content
                level = self._determine_log_level(message)
                
                log_entry = LogEntry(timestamp, level, message, source)
                logs.append(log_entry)
                
            except Exception:
                # Skip malformed log lines
                continue
        
        return logs
    
    async def _get_traditional_logs(self) -> List[LogEntry]:
        """Get logs from traditional log files."""
        logs = []
        
        # Try common log file locations
        log_files = ['/var/log/messages', '/var/log/syslog', '/var/log/kern.log']
        
        for log_file in log_files:
            try:
                output = await run_command(['tail', '-n', '50', log_file])
                if output:
                    logs.extend(self._parse_traditional_log_output(output, log_file))
                    break  # Use the first available log file
            except Exception:
                continue
        
        return logs
    
    def _parse_traditional_log_output(self, output: str, source_file: str) -> List[LogEntry]:
        """Parse traditional syslog format."""
        logs = []
        
        for line in output.split('\n'):
            if not line.strip():
                continue
            
            try:
                # Parse syslog format
                # Format: Jan 01 12:00:00 hostname service: message
                parts = line.split(' ', 4)
                if len(parts) < 5:
                    continue
                
                month_day = f"{parts[0]} {parts[1]}"
                time_str = parts[2]
                hostname = parts[3]
                message = parts[4]
                
                # Construct timestamp (assume current year)
                current_year = datetime.now().year
                timestamp_str = f"{current_year} {month_day} {time_str}"
                timestamp = datetime.strptime(timestamp_str, '%Y %b %d %H:%M:%S')
                
                # Extract service name from message
                service_match = re.match(r'([^:]+):', message)
                source = service_match.group(1) if service_match else source_file
                
                # Determine log level
                level = self._determine_log_level(message)
                
                log_entry = LogEntry(timestamp, level, message, source)
                logs.append(log_entry)
                
            except Exception:
                # Skip malformed log lines
                continue
        
        return logs
    
    def _determine_log_level(self, message: str) -> str:
        """Determine log level from message content."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['critical', 'fatal', 'panic']):
            return 'CRITICAL'
        elif any(word in message_lower for word in ['error', 'failed', 'failure', 'exception']):
            return 'ERROR'
        elif 'warning' in message_lower or 'warn' in message_lower:
            return 'WARNING'
        elif any(word in message_lower for word in ['info', 'information']):
            return 'INFO'
        elif 'debug' in message_lower:
            return 'DEBUG'
        else:
            return 'INFO'  # Default level
    
    def _filter_error_logs(self, logs: List[LogEntry]) -> List[LogEntry]:
        """Filter logs for errors and warnings."""
        error_logs = []
        
        for log in logs:
            # Check if message matches error patterns
            if any(pattern.search(log.message) for pattern in self._compiled_patterns):
                error_logs.append(log)
            # Also include logs with error/warning levels
            elif log.level in ['ERROR', 'CRITICAL', 'WARNING']:
                error_logs.append(log)
        
        return error_logs
    
    def _get_log_statistics(self, all_logs: List[LogEntry], error_logs: List[LogEntry]) -> Dict[str, Any]:
        """Generate log statistics."""
        if not all_logs:
            return {}
        
        # Count by level
        level_counts = {}
        source_counts = {}
        
        for log in all_logs:
            level_counts[log.level] = level_counts.get(log.level, 0) + 1
            source_counts[log.source] = source_counts.get(log.source, 0) + 1
        
        # Time-based statistics
        now = datetime.now()
        recent_errors = len([log for log in error_logs 
                           if (now - log.timestamp.replace(tzinfo=None)).total_seconds() < 300])  # Last 5 minutes
        
        return {
            'total_entries': len(all_logs),
            'error_entries': len(error_logs),
            'recent_errors': recent_errors,
            'level_counts': level_counts,
            'top_sources': dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        }