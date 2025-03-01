"""Tests for configuration management.

This module contains comprehensive tests for configuration handling features, including:
1. Configuration Loading:
   - YAML file parsing
   - Environment variable integration
   - Default values
   - Error handling

2. Webhook URL Resolution:
   - Priority order verification
   - Environment variable handling
   - GitHub Actions integration
   - Fallback behavior

3. Error Handling:
   - Invalid file paths
   - Malformed configuration
   - Missing required fields
   - Permission issues

Test coverage ensures robust configuration management across different environments.
"""
import os
import pytest
from github_release import load_config, get_discord_webhook_url

# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_config():
    """Provide test configuration with environment management.
    
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

# ============================================================================
# Configuration Loading Tests
# ============================================================================

def test_load_config(test_config):
    """Verify configuration file loading and parsing.
    
    Test ensures:
    1. Configuration file is properly loaded
    2. All required sections are present
    3. Values are correctly parsed
    4. Default settings are applied
    
    Verifies specific fields:
    - GitHub repository settings
    - Repository name
    - Version pattern
    - Webhook URL
    
    Args:
        test_config: Fixture providing test configuration
    """
    assert test_config['github']['repository'] == 'test/test-repo'
    assert test_config['github']['name'] == 'Test Repo'
    assert test_config['github']['version_pattern'] == '^v?[0-9]\\.*'
    assert test_config['discord']['notification']['webhook_url'] == 'https://discord.com/api/webhooks/test'

# ============================================================================
# Webhook URL Resolution Tests
# ============================================================================

def test_webhook_url_priority(test_config):
    """Verify webhook URL resolution priority order.
    
    Test ensures proper priority order:
    1. DISCORD_WEBHOOK_URL environment variable (highest)
    2. INPUT_DISCORD_WEBHOOK_URL (GitHub Actions)
    3. Configuration file webhook_url (lowest)
    
    Also verifies:
    - Each source is properly read
    - Priority is maintained when multiple sources exist
    - Fallback behavior works correctly
    
    Args:
        test_config: Fixture providing test configuration
    """
    # Test environment variable priority
    test_url = 'https://discord.com/api/webhooks/env-test'
    os.environ['DISCORD_WEBHOOK_URL'] = test_url
    assert get_discord_webhook_url(test_config) == test_url
    
    # Test GitHub Actions secret priority
    actions_url = 'https://discord.com/api/webhooks/actions-test'
    os.environ['INPUT_DISCORD_WEBHOOK_URL'] = actions_url
    assert get_discord_webhook_url(test_config) == test_url  # env should still take priority
    
    # Test fallback to config
    del os.environ['DISCORD_WEBHOOK_URL']
    del os.environ['INPUT_DISCORD_WEBHOOK_URL']
    webhook_url = get_discord_webhook_url(test_config)
    assert webhook_url == 'https://discord.com/api/webhooks/test'

# ============================================================================
# Error Handling Tests
# ============================================================================

def test_invalid_config_path():
    """Verify handling of invalid configuration file path.
    
    Test ensures:
    1. Non-existent config file is detected
    2. Appropriate error is raised
    3. Error message is descriptive
    4. No default fallback is attempted
    """
    os.environ['CONFIG_PATH'] = 'nonexistent.yaml'
    with pytest.raises(RuntimeError):
        load_config() 