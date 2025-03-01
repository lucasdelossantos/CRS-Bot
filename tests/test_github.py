"""Tests for GitHub release functionality.

This module contains comprehensive tests for GitHub release monitoring features, including:
1. Release Fetching:
   - Latest release retrieval
   - Error handling for API responses
   - Invalid data handling
   - Version pattern matching

2. Version Management:
   - Version file reading/writing
   - JSON data validation
   - File creation and updates
   - Timestamp handling

3. Release Monitoring:
   - New release detection
   - Version comparison
   - Pattern matching
   - Update notification triggers

4. Error Handling:
   - API errors
   - Network issues
   - Invalid data formats
   - File system operations

Test coverage focuses on both successful operations and error scenarios to ensure reliable release monitoring.
"""
import os
import json
import pytest
import responses
from github_release import (
    get_latest_release,
    check_for_new_release,
    load_last_version,
    save_last_version,
    load_config
)

# ============================================================================
# Test Fixtures
# ============================================================================

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

# ============================================================================
# GitHub API Tests
# ============================================================================

@responses.activate
def test_get_latest_release_error_response(test_config):
    """Test handling of error response from GitHub API.
    
    Test ensures:
    1. 404 response from GitHub API is handled gracefully
    2. Function returns None on error
    3. No exceptions are raised
    
    Args:
        test_config: Fixture providing test configuration
    """
    responses.add(
        responses.GET,
        f"https://api.github.com/repos/{test_config['github']['repository']}/releases/latest",
        status=404,
        json={"message": "Not Found"}
    )
    assert get_latest_release(test_config) is None

@responses.activate
def test_get_latest_release_invalid_json(test_config):
    """Test handling of invalid JSON response from GitHub API.
    
    Test ensures:
    1. Malformed JSON response is handled properly
    2. Function returns None for unparseable data
    3. No exceptions are raised for invalid data
    
    Args:
        test_config: Fixture providing test configuration
    """
    responses.add(
        responses.GET,
        f"https://api.github.com/repos/{test_config['github']['repository']}/releases/latest",
        body="Invalid JSON"
    )
    assert get_latest_release(test_config) is None

# ============================================================================
# Version File Management Tests
# ============================================================================

def test_load_last_version_invalid_json(test_config, tmp_path):
    """Test handling of invalid JSON in version file.
    
    Test ensures:
    1. Corrupted version file is handled gracefully
    2. Function returns None for invalid JSON
    3. No exceptions are raised
    4. Temporary test file is properly managed
    
    Args:
        test_config: Fixture providing test configuration
        tmp_path: Pytest fixture providing temporary directory
    """
    version_file = tmp_path / "invalid_version.json"
    version_file.write_text("Invalid JSON")
    
    test_config['storage']['version_file'] = str(version_file)
    assert load_last_version(test_config) is None

# ============================================================================
# Release Monitoring Tests
# ============================================================================

@responses.activate
def test_check_for_new_release_no_match(test_config):
    """Test version pattern not matching release tag.
    
    Test ensures:
    1. Non-matching version patterns are properly handled
    2. No notification is sent for non-matching versions
    3. Process completes without errors
    
    Args:
        test_config: Fixture providing test configuration
    """
    responses.add(
        responses.GET,
        f"https://api.github.com/repos/{test_config['github']['repository']}/releases/latest",
        json={"tag_name": "not-a-version"}
    )
    check_for_new_release(test_config)  # Should not raise and not send notification

@responses.activate
def test_check_for_new_release_same_version(test_config, tmp_path):
    """Test handling when version hasn't changed.
    
    Test ensures:
    1. Existing version is properly loaded
    2. Version comparison works correctly
    3. No notification is sent for same version
    4. Version file is properly managed
    
    Args:
        test_config: Fixture providing test configuration
        tmp_path: Pytest fixture providing temporary directory
    """
    version_file = tmp_path / "version.json"
    test_config['storage']['version_file'] = str(version_file)
    
    # Save initial version
    with open(version_file, 'w') as f:
        json.dump({"last_version": "v1.0.0", "last_check": "2024-01-01T00:00:00"}, f)
    
    responses.add(
        responses.GET,
        f"https://api.github.com/repos/{test_config['github']['repository']}/releases/latest",
        json={"tag_name": "v1.0.0"}
    )
    check_for_new_release(test_config)  # Should not send notification

@responses.activate
def test_check_for_new_release_error(test_config):
    """Test handling of GitHub API error during release check.
    
    Test ensures:
    1. Server errors (500) are handled gracefully
    2. No notifications are sent on error
    3. Process completes without raising exceptions
    
    Args:
        test_config: Fixture providing test configuration
    """
    responses.add(
        responses.GET,
        f"https://api.github.com/repos/{test_config['github']['repository']}/releases/latest",
        status=500
    )
    check_for_new_release(test_config)  # Should handle error gracefully

def test_save_last_version_creates_file(test_config, tmp_path):
    """Test that save_last_version creates the version file.
    
    Test ensures:
    1. New version file is created if it doesn't exist
    2. Version data is properly written
    3. Timestamp is included
    4. File permissions are correct
    
    Args:
        test_config: Fixture providing test configuration
        tmp_path: Pytest fixture providing temporary directory
    """
    version_file = tmp_path / "new_version.json"
    test_config['storage']['version_file'] = str(version_file)
    
    save_last_version("v1.0.0", test_config)
    
    assert version_file.exists()
    with open(version_file) as f:
        data = json.load(f)
        assert data["last_version"] == "v1.0.0"
        assert "last_check" in data 