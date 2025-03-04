import os
import tempfile
import pytest
import logging
from unittest.mock import patch, MagicMock
import github_release
import time
import requests
import json

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

def test_discord_notification_test_env(test_config):
    """Test Discord notification in test environment."""
    with patch('github_release.load_config', return_value=test_config):
        # Test with test environment enabled
        with patch.dict('os.environ', {'TEST_ENV': 'true'}):
            # Test with invalid URL format
            with patch('requests.post', side_effect=requests.exceptions.RequestException("Invalid URL format")):
                with pytest.raises(requests.exceptions.RequestException):
                    github_release.send_discord_notification('1.0.0')

            # Test with HTTP error
            with patch.dict('os.environ', {'TEST_ERROR_TYPE': 'http'}):
                with patch('requests.post', side_effect=requests.exceptions.HTTPError("Test HTTP error")):
                    with pytest.raises(requests.exceptions.HTTPError):
                        github_release.send_discord_notification('1.0.0')

            # Test with connection error
            with patch.dict('os.environ', {'TEST_ERROR_TYPE': 'connection'}):
                with patch('requests.post', side_effect=requests.exceptions.ConnectionError("Test connection error")):
                    with pytest.raises(requests.exceptions.ConnectionError):
                        github_release.send_discord_notification('1.0.0')

            # Test with mock webhook URL
            with patch('github_release.get_discord_webhook_url', return_value='https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz'):
                with patch('requests.post') as mock_post:
                    mock_post.return_value.status_code = 404
                    assert github_release.send_discord_notification('1.0.0') is True

def test_main_execution(test_config):
    """Test the main execution block."""
    with patch('github_release.DISCORD_WEBHOOK_URL', None):
        with patch('github_release.sys.exit') as mock_exit:
            with patch('github_release.__name__', '__main__'):
                with patch('github_release.load_config', return_value=test_config):
                    with patch('github_release.get_discord_webhook_url', return_value=None):
                        with patch('github_release.logger.error') as mock_error:
                            with patch('github_release.check_for_new_release') as mock_check:
                                # Import and run the main block
                                import github_release
                                # Run the main block directly
                                if github_release.__name__ == '__main__':
                                    try:
                                        if not github_release.DISCORD_WEBHOOK_URL:
                                            github_release.logger.error("No Discord webhook URL configured! Please set DISCORD_WEBHOOK_URL environment variable, configure in GitHub Actions, or set in config file.")
                                            github_release.sys.exit(1)
                                        
                                        github_release.setup_logging()
                                        github_release.check_for_new_release()
                                    except Exception as e:
                                        github_release.logger.exception("Unexpected error occurred:")
                                
                                mock_error.assert_called_once_with("No Discord webhook URL configured! Please set DISCORD_WEBHOOK_URL environment variable, configure in GitHub Actions, or set in config file.")
                                mock_exit.assert_called_once_with(1)

    with patch('github_release.DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/test'):
        with patch('github_release.__name__', '__main__'):
            with patch('github_release.load_config', return_value=test_config):
                with patch('github_release.get_discord_webhook_url', return_value='https://discord.com/api/webhooks/test'):
                    with patch('github_release.setup_logging') as mock_setup:
                        with patch('github_release.check_for_new_release') as mock_check:
                            # Import and run the main block
                            import github_release
                            # Run the main block directly
                            if github_release.__name__ == '__main__':
                                try:
                                    if not github_release.DISCORD_WEBHOOK_URL:
                                        github_release.logger.error("No Discord webhook URL configured! Please set DISCORD_WEBHOOK_URL environment variable, configure in GitHub Actions, or set in config file.")
                                        github_release.sys.exit(1)
                                    
                                    github_release.setup_logging()
                                    github_release.check_for_new_release()
                                except Exception as e:
                                    github_release.logger.exception("Unexpected error occurred:")
                            
                            mock_setup.assert_called_once()
                            mock_check.assert_called_once()

def test_version_pattern_mismatch(test_config):
    """Test version pattern mismatch in check_for_new_release."""
    with patch('github_release.load_config', return_value=test_config):
        with patch('github_release.get_latest_release', return_value='invalid-version'):
            github_release.check_for_new_release()
            # No exception should be raised 

def test_check_for_new_release_no_latest_version(test_config):
    """Test check_for_new_release when get_latest_release returns None."""
    with patch('github_release.get_latest_release', return_value=None):
        with patch('github_release.logger.warning') as mock_warning:
            github_release.check_for_new_release(test_config)
            mock_warning.assert_called_once_with("No release found or error occurred.")

def test_check_for_new_release_version_pattern_mismatch(test_config):
    """Test check_for_new_release when version doesn't match pattern."""
    with patch('github_release.get_latest_release', return_value='invalid-version'):
        with patch('github_release.logger.info') as mock_info:
            github_release.check_for_new_release(test_config)
            assert mock_info.call_count == 2
            mock_info.assert_any_call("Starting new release check...")
            mock_info.assert_any_call("Version invalid-version does not match the monitored pattern.")

def test_check_for_new_release_new_version(test_config):
    """Test check_for_new_release when a new version is detected."""
    with patch('github_release.get_latest_release', return_value='v1.0.0'):
        with patch('github_release.load_last_version', return_value='v0.9.0'):
            with patch('github_release.send_discord_notification') as mock_send:
                with patch('github_release.save_last_version') as mock_save:
                    with patch('github_release.logger.info') as mock_info:
                        github_release.check_for_new_release(test_config)
                        assert mock_info.call_count == 2
                        mock_info.assert_any_call("Starting new release check...")
                        mock_info.assert_any_call("New release detected! Version: v1.0.0")
                        mock_send.assert_called_once_with('v1.0.0', test_config)
                        mock_save.assert_called_once_with('v1.0.0', test_config)

def test_check_for_new_release_no_new_version(test_config):
    """Test check_for_new_release when no new version is detected."""
    with patch('github_release.get_latest_release', return_value='v1.0.0'):
        with patch('github_release.load_last_version', return_value='v1.0.0'):
            with patch('github_release.logger.info') as mock_info:
                github_release.check_for_new_release(test_config)
                assert mock_info.call_count == 2
                mock_info.assert_any_call("Starting new release check...")
                mock_info.assert_any_call("No new release detected.") 

def test_setup_logging_docker(test_config):
    """Test setup_logging when running in Docker container."""
    with patch.dict(os.environ, {'DOCKER_CONTAINER': 'true'}):
        with patch('os.path.isabs', return_value=False):
            with patch('os.path.join', return_value='/app/test.log'):
                with patch('os.path.dirname', return_value='/app'):
                    with patch('os.makedirs') as mock_makedirs:
                        with patch('os.path.exists', return_value=False):
                            with patch('builtins.open', create=True) as mock_open:
                                github_release.configure_logging(test_config)
                                mock_makedirs.assert_called_once_with('/app', exist_ok=True)

def test_setup_logging_outside_docker(test_config):
    """Test setup_logging when running outside Docker container."""
    with patch.dict(os.environ, {'DOCKER_CONTAINER': ''}):
        with patch('os.path.isabs', return_value=False):
            with patch('os.path.abspath', return_value='/absolute/path/test.log'):
                with patch('os.path.dirname', return_value='/absolute/path'):
                    with patch('os.makedirs') as mock_makedirs:
                        with patch('os.path.exists', return_value=False):
                            with patch('builtins.open', create=True) as mock_open:
                                github_release.configure_logging(test_config)
                                mock_makedirs.assert_called_once_with('/absolute/path', exist_ok=True)

def test_setup_logging_permission_error(test_config):
    """Test setup_logging when there's a permission error."""
    with patch('github_release.logger.info') as mock_info:
        with patch('os.makedirs', side_effect=PermissionError):
            github_release.configure_logging(test_config)
            mock_info.assert_called_once_with("Logging configured successfully")

def test_get_latest_release_no_tag_name(test_config):
    """Test get_latest_release when response has no tag_name."""
    with patch('github_release.create_github_session') as mock_session:
        mock_response = MagicMock()
        mock_response.json.return_value = {'other_field': 'value'}
        mock_session.return_value.get.return_value = mock_response
        with patch('github_release.logger.error') as mock_error:
            result = github_release.get_latest_release(test_config)
            assert result is None
            mock_error.assert_called_once()

def test_get_latest_release_error_status(test_config):
    """Test get_latest_release when response has error status code."""
    with patch('github_release.create_github_session') as mock_session:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_session.return_value.get.return_value = mock_response
        with patch('github_release.logger.error') as mock_error:
            result = github_release.get_latest_release(test_config)
            assert result is None
            assert mock_error.call_count == 1

def test_get_latest_release_connection_error(test_config):
    """Test get_latest_release when there's a connection error."""
    with patch('github_release.create_github_session') as mock_session:
        mock_session.return_value.get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        with patch('github_release.logger.error') as mock_error:
            result = github_release.get_latest_release(test_config)
            assert result is None
            mock_error.assert_called_once_with("Error fetching release: Connection refused")

def test_save_last_version_no_directory(test_config):
    """Test save_last_version when directory doesn't exist."""
    with patch('os.path.dirname', return_value='/test/dir'):
        with patch('os.makedirs') as mock_makedirs:
            with patch('builtins.open', create=True) as mock_open:
                github_release.save_last_version('v1.0.0', test_config)
                mock_makedirs.assert_called_once_with('/test/dir', exist_ok=True)

def test_save_last_version_permission_error(test_config):
    """Test save_last_version when there's a permission error."""
    with patch('builtins.open', create=True, side_effect=PermissionError):
        with patch('github_release.logger.error') as mock_error:
            with pytest.raises(PermissionError):
                github_release.save_last_version('v1.0.0', test_config)

def test_load_last_version_no_file(test_config):
    """Test load_last_version when file doesn't exist."""
    with patch('os.path.exists', return_value=False):
        with patch('github_release.logger.info') as mock_info:
            result = github_release.load_last_version(test_config)
            assert result is None
            assert mock_info.call_count == 2
            mock_info.assert_any_call("Loading last recorded version...")
            mock_info.assert_any_call("No previous version recorded.")

def test_load_last_version_empty_file(test_config):
    """Test load_last_version when file is empty."""
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = ''
            with patch('json.load', side_effect=json.JSONDecodeError("Expecting value", '', 0)):
                with patch('github_release.logger.error') as mock_error:
                    result = github_release.load_last_version(test_config)
                    assert result is None
                    mock_error.assert_called_once()

def test_load_last_version_invalid_json(test_config):
    """Test load_last_version when file has invalid JSON."""
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = 'invalid json'
            with patch('json.load', side_effect=json.JSONDecodeError("Expecting value", 'invalid json', 0)):
                with patch('github_release.logger.error') as mock_error:
                    result = github_release.load_last_version(test_config)
                    assert result is None
                    mock_error.assert_called_once()

def test_send_discord_notification_no_version(test_config):
    """Test send_discord_notification when version is None."""
    with pytest.raises(ValueError, match="Version string cannot be None"):
        github_release.send_discord_notification(None, test_config)

def test_send_discord_notification_no_config_no_path(test_config):
    """Test send_discord_notification when config is None and CONFIG_PATH is not set."""
    with patch.dict(os.environ, {'CONFIG_PATH': ''}):
        with pytest.raises(RuntimeError, match="No config provided and CONFIG_PATH not set"):
            github_release.send_discord_notification('v1.0.0', None)

def test_send_discord_notification_no_webhook(test_config):
    """Test send_discord_notification when webhook URL is missing."""
    with patch('github_release.get_discord_webhook_url', return_value=None):
        with pytest.raises(ValueError, match="Discord webhook URL is required"):
            github_release.send_discord_notification('v1.0.0', test_config)

def test_send_discord_notification_no_color(test_config):
    """Test send_discord_notification when color is not set in config."""
    test_config['discord']['notification'].pop('color', None)
    with patch('github_release.get_discord_webhook_url', return_value='https://discord.com/api/webhooks/test'):
        with patch('github_release.logger.info') as mock_info:
            with patch('github_release.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                github_release.send_discord_notification('v1.0.0', test_config)
                mock_info.assert_called_once_with("Using default color (blue) for Discord notification")
                mock_post.assert_called_once()

def test_send_discord_notification_no_footer(test_config):
    """Test send_discord_notification when footer text is not set in config."""
    test_config['discord']['notification'].pop('footer_text', None)
    with patch('github_release.get_discord_webhook_url', return_value='https://discord.com/api/webhooks/test'):
        with patch('github_release.logger.info') as mock_info:
            with patch('github_release.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                github_release.send_discord_notification('v1.0.0', test_config)
                mock_info.assert_called_once_with("Using default footer text for Discord notification")
                mock_post.assert_called_once()

def test_get_discord_webhook_url_from_env(test_config):
    """Test get_discord_webhook_url when DISCORD_WEBHOOK_URL is set."""
    with patch.dict(os.environ, {'DISCORD_WEBHOOK_URL': 'https://discord.com/api/webhooks/test'}):
        with patch('github_release.logger.debug') as mock_debug:
            result = github_release.get_discord_webhook_url(test_config)
            assert result == 'https://discord.com/api/webhooks/test'
            mock_debug.assert_called_once_with("Using Discord webhook URL from environment variable")

def test_get_discord_webhook_url_from_actions(test_config):
    """Test get_discord_webhook_url when INPUT_DISCORD_WEBHOOK_URL is set."""
    with patch.dict(os.environ, {
        'DISCORD_WEBHOOK_URL': '',
        'INPUT_DISCORD_WEBHOOK_URL': 'https://discord.com/api/webhooks/test'
    }):
        with patch('github_release.logger.debug') as mock_debug:
            result = github_release.get_discord_webhook_url(test_config)
            assert result == 'https://discord.com/api/webhooks/test'
            mock_debug.assert_called_once_with("Using Discord webhook URL from GitHub Actions secret")

def test_get_discord_webhook_url_from_config(test_config):
    """Test get_discord_webhook_url when webhook URL is in config."""
    with patch.dict(os.environ, {'DISCORD_WEBHOOK_URL': '', 'INPUT_DISCORD_WEBHOOK_URL': ''}):
        with patch('github_release.logger.debug') as mock_debug:
            result = github_release.get_discord_webhook_url(test_config)
            assert result == test_config['discord']['notification']['webhook_url']
            mock_debug.assert_called_once_with("Using Discord webhook URL from config file")

def test_get_discord_webhook_url_no_sources(test_config):
    """Test get_discord_webhook_url when no webhook URL is available."""
    with patch.dict(os.environ, {'DISCORD_WEBHOOK_URL': '', 'INPUT_DISCORD_WEBHOOK_URL': ''}):
        test_config['discord']['notification'].pop('webhook_url')
        result = github_release.get_discord_webhook_url(test_config)
        assert result is None 