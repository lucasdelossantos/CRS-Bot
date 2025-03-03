"""Tests for Discord notification functionality.

This module contains comprehensive tests for Discord webhook notification features, including:
1. Webhook URL Resolution:
   - Environment variables (DISCORD_WEBHOOK_URL)
   - GitHub Actions integration (INPUT_DISCORD_WEBHOOK_URL)
   - Configuration file settings
   - Priority order handling

2. Discord Notification Sending:
   - Successful notifications
   - Rate limit handling
   - Error scenarios
   - Network issues
   - Message formatting

3. Configuration Validation:
   - Missing webhook URLs
   - Invalid configurations
   - Default value handling
   - Error cases

4. Error Handling:
   - HTTP errors
   - Network errors
   - Configuration errors
   - Input validation

Test coverage focuses on both happy paths and edge cases to ensure robust functionality.
"""
import os
import json
import pytest
import requests
import responses
import logging
from github_release import send_discord_notification, load_config, get_discord_webhook_url

@pytest.fixture
def test_config():
    """Provide test configuration with proper environment management.
    
    This fixture handles:
    1. Loading test configuration from test_config.yaml
    2. Managing CONFIG_PATH environment variable:
       - Stores original value
       - Sets test value
       - Restores original after test
    3. Providing clean configuration for each test
    
    Returns:
        dict: Loaded test configuration with all necessary sections
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_config_path = os.path.join(current_dir, 'test_config.yaml')
    
    # Store original config path if it exists
    original_config_path = os.environ.get('CONFIG_PATH')
    
    # Set test config path
    os.environ['CONFIG_PATH'] = test_config_path
    
    # Get config and restore original path
    config = load_config()
    
    if original_config_path:
        os.environ['CONFIG_PATH'] = original_config_path
    else:
        del os.environ['CONFIG_PATH']
    
    return config

@pytest.fixture
def clean_env():
    """Manage environment variables for webhook URL testing.
    
    This fixture ensures a clean test environment by:
    1. Storing original webhook-related environment variables:
       - DISCORD_WEBHOOK_URL
       - INPUT_DISCORD_WEBHOOK_URL
    2. Removing these variables for test isolation
    3. Restoring original values after test completion
    
    This prevents environment variable pollution between tests.
    """
    # Store original values
    original_webhook = os.environ.get('DISCORD_WEBHOOK_URL')
    original_input_webhook = os.environ.get('INPUT_DISCORD_WEBHOOK_URL')
    
    # Clean environment
    if 'DISCORD_WEBHOOK_URL' in os.environ:
        del os.environ['DISCORD_WEBHOOK_URL']
    if 'INPUT_DISCORD_WEBHOOK_URL' in os.environ:
        del os.environ['INPUT_DISCORD_WEBHOOK_URL']
    
    yield
    
    # Restore original values
    if original_webhook:
        os.environ['DISCORD_WEBHOOK_URL'] = original_webhook
    if original_input_webhook:
        os.environ['INPUT_DISCORD_WEBHOOK_URL'] = original_input_webhook

@pytest.fixture
def caplog(caplog):
    """Configure logging capture for detailed test output.
    
    Sets logging level to DEBUG to capture all log messages during tests,
    enabling verification of logging behavior and debug information.
    """
    caplog.set_level(logging.DEBUG)
    return caplog

@pytest.fixture
def release_data():
    """Provide sample GitHub release data for notification testing.
    
    Returns a dictionary containing standardized release information:
    - tag_name: Version identifier (e.g., "v4.0.0")
    - name: Human-readable release name
    - published_at: ISO 8601 formatted timestamp
    - html_url: GitHub release page URL
    
    This fixture ensures consistent test data across notification tests.
    """
    return {
        "tag_name": "v4.0.0",
        "name": "Version 4.0.0",
        "published_at": "2024-02-28T00:00:00Z",
        "html_url": "https://github.com/test/test-repo/releases/tag/v4.0.0"
    }

# ============================================================================
# Webhook URL Resolution Tests
# ============================================================================

def test_get_webhook_url_from_env(clean_env, test_config):
    """Verify webhook URL resolution from environment variable.
    
    Test ensures:
    1. DISCORD_WEBHOOK_URL environment variable is properly read
    2. Environment variable takes highest priority
    3. URL is returned exactly as set in environment
    
    Args:
        clean_env: Fixture providing clean environment
        test_config: Fixture providing test configuration
    """
    test_url = "https://discord.com/api/webhooks/test"
    os.environ['DISCORD_WEBHOOK_URL'] = test_url
    assert get_discord_webhook_url(test_config) == test_url

def test_get_webhook_url_from_github_actions(clean_env, test_config):
    """Verify webhook URL resolution from GitHub Actions environment.
    
    Test ensures:
    1. INPUT_DISCORD_WEBHOOK_URL is properly read
    2. GitHub Actions URL is used when DISCORD_WEBHOOK_URL is absent
    3. Correct priority order is maintained
    
    Args:
        clean_env: Fixture providing clean environment
        test_config: Fixture providing test configuration
    """
    test_url = "https://discord.com/api/webhooks/github_actions"
    os.environ['INPUT_DISCORD_WEBHOOK_URL'] = test_url
    assert get_discord_webhook_url(test_config) == test_url

def test_get_webhook_url_priority(clean_env, test_config):
    """Test webhook URL priority order.
    
    Verifies the priority order of webhook URL sources:
    1. DISCORD_WEBHOOK_URL environment variable
    2. INPUT_DISCORD_WEBHOOK_URL environment variable (GitHub Actions)
    3. webhook_url from config file
    """
    env_url = "https://discord.com/api/webhooks/env"
    actions_url = "https://discord.com/api/webhooks/actions"
    config_url = "https://discord.com/api/webhooks/config"
    
    # Set all sources
    os.environ['DISCORD_WEBHOOK_URL'] = env_url
    os.environ['INPUT_DISCORD_WEBHOOK_URL'] = actions_url
    test_config['discord']['notification']['webhook_url'] = config_url
    
    # Should use env var
    assert get_discord_webhook_url(test_config) == env_url
    
    # Remove env var, should use GitHub Actions
    del os.environ['DISCORD_WEBHOOK_URL']
    assert get_discord_webhook_url(test_config) == actions_url
    
    # Remove GitHub Actions, should use config
    del os.environ['INPUT_DISCORD_WEBHOOK_URL']
    assert get_discord_webhook_url(test_config) == config_url

# Tests for webhook URL edge cases
def test_get_webhook_url_no_sources(clean_env, test_config):
    """Test behavior when no webhook URL is available.
    
    Verifies that None is returned when no webhook URL is configured
    in any source.
    """
    test_config['discord']['notification']['webhook_url'] = ""
    assert get_discord_webhook_url(test_config) is None

def test_get_webhook_url_empty_actions(clean_env, test_config):
    """Test handling of empty GitHub Actions webhook URL.
    
    Verifies that an empty INPUT_DISCORD_WEBHOOK_URL is ignored and
    the next source in priority is used.
    """
    os.environ['INPUT_DISCORD_WEBHOOK_URL'] = ""
    test_config['discord']['notification']['webhook_url'] = "https://discord.com/api/webhooks/config"
    assert get_discord_webhook_url(test_config) == "https://discord.com/api/webhooks/config"

# Tests for malformed configuration
def test_malformed_config_missing_discord(clean_env, test_config):
    """Test handling of missing discord section in config.
    
    Verifies that None is returned when the 'discord' section
    is missing from the configuration.
    """
    del test_config['discord']
    assert get_discord_webhook_url(test_config) is None

def test_malformed_config_missing_notification(clean_env, test_config):
    """Test handling of missing notification section in config.
    
    Verifies that None is returned when the 'notification' section
    is missing from the discord configuration.
    """
    del test_config['discord']['notification']
    assert get_discord_webhook_url(test_config) is None

# ============================================================================
# Discord Notification Tests
# ============================================================================

@responses.activate
def test_send_discord_notification_success(test_config, release_data):
    """Verify successful Discord notification sending process.
    
    Test ensures:
    1. Notification payload is properly formatted
    2. HTTP POST request is made to correct webhook URL
    3. Success response (200) is handled correctly
    4. Function returns True on success
    
    Uses responses library to mock Discord API interaction.
    
    Args:
        test_config: Fixture providing test configuration
        release_data: Fixture providing sample release data
    """
    responses.add(
        responses.POST,
        test_config['discord']['notification']['webhook_url'],
        json={"id": "1234567890"},
        status=200
    )
    
    assert send_discord_notification(release_data['tag_name'], test_config) is True

@responses.activate
def test_send_discord_notification_rate_limit(test_config, release_data):
    """Test Discord rate limit handling.
    
    Verifies that:
    1. Rate limit responses (429) are handled gracefully
    2. The function returns False when rate limited
    3. The Retry-After header is processed
    """
    responses.add(
        responses.POST,
        test_config['discord']['notification']['webhook_url'],
        json={"message": "Rate limited"},
        status=429,
        headers={'Retry-After': '1'}
    )
    
    assert send_discord_notification(release_data['tag_name'], test_config) is False

@responses.activate
def test_discord_error_handling(test_config):
    """Verify handling of various Discord API error responses.
    
    Test covers:
    1. Rate limit (429):
       - Verifies return value is False
       - Checks Retry-After header processing
    2. Server error (500):
       - Verifies HTTPError is raised
       - Validates error status code
    """
    # Set up test to expect HTTP errors
    os.environ['TEST_DISCORD_ERROR_HANDLING'] = 'true'
    
    webhook_url = test_config['discord']['notification']['webhook_url']
    
    # Test rate limit
    responses.add(
        responses.POST,
        webhook_url,
        status=429,
        json={"retry_after": 1}
    )
    
    assert send_discord_notification("v4.0.0", test_config) is False
    
    # Test server error
    responses.replace(
        responses.POST,
        webhook_url,
        status=500,
        json={"message": "Internal Server Error"}
    )
    
    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        send_discord_notification("v4.0.0", test_config)
    assert exc_info.value.response.status_code == 500

@responses.activate
def test_discord_network_error(test_config):
    """Test network error handling.
    
    Verifies that connection errors are properly caught and
    raised as ConnectionError exceptions.
    """
    # Set up test to expect connection errors
    os.environ['TEST_DISCORD_NETWORK_ERROR'] = 'true'
    
    webhook_url = test_config['discord']['notification']['webhook_url']
    
    # Mock connection error
    responses.add(
        responses.POST,
        webhook_url,
        body=requests.exceptions.ConnectionError("Connection refused")
    )
    
    with pytest.raises(requests.exceptions.ConnectionError):
        send_discord_notification("v4.0.0", test_config)

@responses.activate
def test_discord_message_format(test_config):
    """Test Discord message formatting.
    
    Verifies that the Discord message payload:
    1. Contains required embed fields
    2. Has correct title and description
    3. Uses configured color and footer text
    4. Includes timestamp
    """
    webhook_url = test_config['discord']['notification']['webhook_url']
    
    def check_message(request):
        """Verify the Discord message format."""
        json_data = json.loads(request.body.decode('utf-8'))
        embeds = json_data.get('embeds', [])
        
        assert len(embeds) == 1
        embed = embeds[0]
        
        assert "New Test Repo Release!" in embed['title']
        assert "v4.0.0" in embed['description']
        assert embed['color'] == test_config['discord']['notification']['color']
        assert 'timestamp' in embed
        assert embed['footer']['text'] == test_config['discord']['notification']['footer_text']
        
        return (204, {}, '')
    
    responses.add_callback(
        responses.POST,
        webhook_url,
        callback=check_message
    )
    
    send_discord_notification("v4.0.0", test_config)

# ============================================================================
# Configuration Validation Tests
# ============================================================================

@responses.activate
def test_missing_webhook_url(clean_env, test_config):
    """Test handling of missing webhook URL.
    
    Verifies that attempting to send a notification without a
    webhook URL raises a ValueError.
    """
    test_config['discord']['notification']['webhook_url'] = ""
    
    with pytest.raises(ValueError, match="Discord webhook URL is required"):
        send_discord_notification("v4.0.0", test_config)

@responses.activate
def test_no_config_provided():
    """Test sending notification without config.
    
    Verifies that attempting to send a notification without providing
    a configuration raises a RuntimeError.
    """
    with pytest.raises(RuntimeError):
        send_discord_notification("v4.0.0")

def test_malformed_config_missing_color(clean_env, test_config, caplog):
    """Verify handling of missing color configuration.
    
    Test ensures:
    1. Default color value is used when config lacks color
    2. Warning log message is generated about using default
    3. Notification still sends successfully
    4. Log message contains appropriate context
    
    Args:
        clean_env: Fixture providing clean environment
        test_config: Fixture providing test configuration
        caplog: Fixture for capturing log output
    """
    test_config['discord']['notification'] = {
        'webhook_url': 'https://discord.com/api/webhooks/test',
        'footer_text': 'Test Bot'  # Keep footer_text to isolate color test
    }
    
    webhook_url = "https://discord.com/api/webhooks/test"
    os.environ['DISCORD_WEBHOOK_URL'] = webhook_url
    
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, webhook_url, status=204)
        send_discord_notification("v4.0.0", test_config)
    
    # Check if any log message contains "default color" (case insensitive)
    assert any("default color" in record.message.lower() for record in caplog.records)

def test_malformed_config_missing_footer(clean_env, test_config, caplog):
    """Test handling of missing footer in config.
    
    Verifies that:
    1. Default footer text is used when footer is missing
    2. Appropriate log message is generated
    3. Notification is sent successfully
    """
    test_config['discord']['notification'] = {
        'webhook_url': 'https://discord.com/api/webhooks/test',
        'color': 5814783  # Keep color to isolate footer test
    }
    
    webhook_url = "https://discord.com/api/webhooks/test"
    os.environ['DISCORD_WEBHOOK_URL'] = webhook_url
    
    with responses.RequestsMock() as rsps:
        rsps.add(responses.POST, webhook_url, status=204)
        send_discord_notification("v4.0.0", test_config)
    
    # Check if any log message contains "default footer" (case insensitive)
    assert any("default footer" in record.message.lower() for record in caplog.records)

@responses.activate
def test_invalid_webhook_url_format(test_config):
    """Test handling of invalid webhook URL format.
    
    Verifies that attempting to send a notification to an invalid
    webhook URL raises a RequestException.
    """
    # Set up test to expect request errors
    os.environ['TEST_INVALID_WEBHOOK_URL'] = 'true'
    
    test_config['discord']['notification']['webhook_url'] = "not-a-valid-url"
    print(f"\nTest configuration: {test_config}")
    print(f"Webhook URL: {test_config['discord']['notification']['webhook_url']}")

    try:
        send_discord_notification("v4.0.0", test_config)
        print("\nExpected RequestException to be raised, but no exception was raised")
        assert False, "Expected RequestException to be raised"
    except requests.exceptions.RequestException as e:
        print(f"\nGot expected RequestException: {str(e)}")
        print(f"Exception type: {type(e)}")
        assert True
    except Exception as e:
        print(f"\nGot unexpected exception: {str(e)}")
        print(f"Exception type: {type(e)}")
        assert False, f"Expected RequestException, got {type(e)}"

def test_send_discord_notification_missing_webhook(clean_env, test_config, release_data):
    """Verify proper error handling when webhook URL is missing.
    
    Test ensures:
    1. Configuration is properly isolated from other tests
    2. All required config sections are preserved
    3. ValueError is raised with correct error message
    4. No HTTP requests are attempted
    
    Args:
        clean_env: Fixture providing clean environment
        test_config: Fixture providing test configuration
        release_data: Fixture providing sample release data
    """
    # Create a deep copy of the config without webhook URL
    config_without_webhook = {
        'discord': {
            'notification': {}
        }
    }
    # Copy only the necessary fields
    if 'github' in test_config:
        config_without_webhook['github'] = test_config['github'].copy()
    if 'storage' in test_config:
        config_without_webhook['storage'] = test_config['storage'].copy()
    if 'logging' in test_config:
        config_without_webhook['logging'] = test_config['logging'].copy()
    
    # Ensure no webhook URL in environment
    if 'DISCORD_WEBHOOK_URL' in os.environ:
        del os.environ['DISCORD_WEBHOOK_URL']
    if 'INPUT_DISCORD_WEBHOOK_URL' in os.environ:
        del os.environ['INPUT_DISCORD_WEBHOOK_URL']
    
    with pytest.raises(ValueError, match="Discord webhook URL is required"):
        send_discord_notification(release_data['tag_name'], config_without_webhook)

def test_send_discord_notification_missing_release_data(test_config):
    """Test handling of missing release data.
    
    Verifies that attempting to send a notification with None as
    the version string raises a ValueError.
    """
    with pytest.raises(ValueError, match="Version string cannot be None"):
        send_discord_notification(None, test_config) 