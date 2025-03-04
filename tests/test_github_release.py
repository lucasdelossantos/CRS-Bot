import os
import tempfile
import pytest
import logging
from unittest.mock import patch, MagicMock
import github_release
import time
import requests

@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def test_config(temp_log_dir):
    """Create a test configuration."""
    return {
        'logging': {
            'file': os.path.join(temp_log_dir, 'test.log'),
            'level': 'INFO',
            'format': '%(asctime)s - %(levelname)s - %(message)s'
        },
        'github': {
            'repository': 'test/repo',
            'name': 'Test Repo',
            'version_pattern': r'v\d+\.\d+\.\d+',
            'api': {
                'retries': 3,
                'backoff_factor': 1,
                'status_forcelist': [500, 502, 503, 504],
                'headers': {
                    'accept': 'application/vnd.github.v3+json',
                    'user_agent': 'CRS-Bot'
                }
            }
        },
        'storage': {
            'version_file': os.path.join(temp_log_dir, 'last_version.json')
        },
        'discord': {
            'notification': {
                'webhook_url': 'https://discord.com/api/webhooks/test',
                'color': 5814783,
                'footer_text': 'CRS-Bot'
            }
        }
    }

def test_logging_configuration(test_config):
    """Test that logging is properly configured with file and console handlers."""
    with patch('github_release.load_config', return_value=test_config):
        # Configure logging
        github_release.configure_logging(test_config)
        
        # Verify that the logger has both file and console handlers
        assert len(github_release.logger.handlers) == 2
        
        # Verify handler types
        handler_types = [type(h) for h in github_release.logger.handlers]
        assert logging.FileHandler in handler_types
        assert logging.StreamHandler in handler_types
        
        # Test logging
        test_message = "Test log message"
        github_release.logger.info(test_message)
        
        # Verify the log file was created and contains the message
        assert os.path.exists(test_config['logging']['file'])
        with open(test_config['logging']['file'], 'r') as f:
            log_content = f.read()
            assert test_message in log_content

def test_logging_permissions(test_config):
    """Test that logging works with the correct permissions."""
    with patch('github_release.load_config', return_value=test_config):
        # Configure logging
        github_release.configure_logging(test_config)
        
        # Test logging with different permission scenarios
        test_message = "Test log message"
        github_release.logger.info(test_message)
        
        # Verify file permissions
        log_file = test_config['logging']['file']
        assert os.path.exists(log_file)
        
        # Test file is writable
        try:
            with open(log_file, 'a') as f:
                f.write("Additional test message\n")
        except PermissionError:
            pytest.fail("Log file is not writable")

def test_logging_initialization():
    """Test that logging is properly initialized at module level."""
    # Verify that the logger is created at module level
    assert hasattr(github_release, 'logger')
    assert isinstance(github_release.logger, logging.Logger)
    
    # Verify that the logger name is correct
    assert github_release.logger.name == 'github_release'

def test_logging_handlers_cleanup(test_config):
    """Test that existing handlers are removed before reconfiguration."""
    with patch('github_release.load_config', return_value=test_config):
        # Configure logging twice
        github_release.configure_logging(test_config)
        initial_handlers = github_release.logger.handlers.copy()
        
        github_release.configure_logging(test_config)
        final_handlers = github_release.logger.handlers
        
        # Verify that the handlers were properly cleaned up
        assert len(final_handlers) == 2  # Should have exactly 2 handlers
        assert final_handlers != initial_handlers  # Should be new handlers

def test_logging_setup_function(test_config):
    """Test the setup_logging function."""
    with patch('github_release.load_config', return_value=test_config):
        # Ensure log directory exists and is writable
        log_dir = os.path.dirname(test_config['logging']['file'])
        os.makedirs(log_dir, exist_ok=True)
        
        # Create the log file with correct permissions using tempfile
        log_file = os.path.abspath(test_config['logging']['file'])
        with tempfile.NamedTemporaryFile(mode='w', dir=log_dir, delete=False) as temp:
            temp.write("")  # Create empty file
            os.rename(temp.name, log_file)
            os.chmod(log_file, 0o600)  # nosec B103: This is a test environment with a temporary file
        
        # Update the config to use the absolute path
        test_config['logging']['file'] = log_file
        
        # Configure logging directly
        github_release.configure_logging(test_config)
        
        # Verify that logging is configured
        assert len(github_release.logger.handlers) == 2
        
        # Test that logging works
        test_message = "Test setup_logging message"
        github_release.logger.info(test_message)
        
        # Force flush all handlers
        for handler in github_release.logger.handlers:
            handler.flush()
        
        # Verify the message was logged
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert test_message in log_content, f"Expected '{test_message}' in log content: '{log_content}'"

def test_error_handling(test_config):
    """Test error handling in various functions."""
    # Test config loading error
    with patch('builtins.open', side_effect=Exception("Test error")):
        with pytest.raises(RuntimeError) as exc_info:
            github_release.load_config()
        assert "Failed to load configuration" in str(exc_info.value)
        assert "Test error" in str(exc_info.value)

    # Test webhook URL error
    with patch.dict('os.environ', {}, clear=True):
        with patch('github_release.load_config', return_value={'discord': {'notification': {}}}):
            assert github_release.get_discord_webhook_url() is None

    # Test GitHub API error
    with patch('requests.get', side_effect=requests.exceptions.RequestException):
        with patch('github_release.load_config', return_value=test_config):
            assert github_release.get_latest_release() is None

    # Test version checking error
    with patch('github_release.get_latest_release', return_value=None):
        with patch('github_release.load_config', return_value=test_config):
            assert github_release.check_for_new_release() is None

    # Test file operation errors
    with patch('builtins.open', side_effect=OSError):
        with patch('github_release.load_config', return_value=test_config):
            assert github_release.load_last_version() is None

    # Test Discord notification error
    with patch('requests.post', side_effect=requests.exceptions.RequestException):
        with patch('github_release.load_config', return_value=test_config):
            with pytest.raises(requests.exceptions.RequestException):
                github_release.send_discord_notification('1.0.0')

def test_logging_error_handling(test_config):
    """Test error handling in logging configuration."""
    with patch('github_release.load_config', return_value=test_config):
        # Test logging configuration error
        with patch('logging.FileHandler', side_effect=Exception("Test error")):
            with pytest.raises(Exception) as exc_info:
                github_release.configure_logging(test_config)
            assert "Test error" in str(exc_info.value)

def test_file_operation_error_handling(test_config):
    """Test error handling in file operations."""
    with patch('github_release.load_config', return_value=test_config):
        # Test file operation error
        with patch('builtins.open', side_effect=PermissionError("Test error")):
            with pytest.raises(PermissionError) as exc_info:
                github_release.save_last_version("1.0.0", test_config)
            assert "Test error" in str(exc_info.value) 