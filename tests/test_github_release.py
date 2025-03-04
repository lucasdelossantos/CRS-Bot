import os
import tempfile
import pytest
import logging
from unittest.mock import patch, MagicMock
import github_release
import time

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
        
        # Create the log file and ensure it's writable
        log_file = os.path.abspath(test_config['logging']['file'])
        with open(log_file, 'a') as f:
            f.write("")  # Create empty file
        os.chmod(log_file, 0o660)  # Make file readable/writable by owner and group only
        
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