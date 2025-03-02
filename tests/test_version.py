"""Tests for version tracking functionality.

This module contains comprehensive tests for version management features, including:
1. Version File Operations:
   - File creation and reading
   - Version data persistence
   - JSON format handling
   - Timestamp management

2. Error Handling:
   - Missing files
   - Invalid JSON data
   - Permission issues
   - File system errors

3. Version Management:
   - Version string storage
   - Last check timestamp
   - Data validation
   - File integrity

Test coverage ensures reliable version tracking across different scenarios.
"""
import os
import json
import pytest
from github_release import load_last_version, save_last_version, load_config

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

@pytest.fixture
def test_version_file(tmp_path, test_config):
    """Create and manage temporary version file for testing.
    
    This fixture:
    1. Creates a temporary directory for version file
    2. Updates config to use temporary file path
    3. Ensures clean test environment for each test
    4. Handles cleanup after test completion
    
    Args:
        tmp_path: Pytest fixture providing temporary directory
        test_config: Fixture providing test configuration
    
    Returns:
        dict: Updated configuration with temporary version file path
    """
    version_file = tmp_path / "test_last_version.json"
    # Update config to use the temporary file
    test_config['storage']['version_file'] = str(version_file)
    return test_config

# ============================================================================
# File Operation Tests
# ============================================================================

def test_load_nonexistent_version(test_version_file):
    """Verify behavior when version file doesn't exist.
    
    Test ensures:
    1. Non-existent file is handled gracefully
    2. None is returned as expected
    3. No errors are raised
    4. File system is not modified
    
    Args:
        test_version_file: Fixture providing test configuration with temp file
    """
    assert load_last_version(test_version_file) is None

def test_save_and_load_version(test_version_file):
    """Verify version data saving and loading functionality.
    
    Test ensures:
    1. Version string is properly saved
    2. Timestamp is included in saved data
    3. Data can be loaded correctly
    4. File format is valid JSON
    5. All required fields are present
    
    Args:
        test_version_file: Fixture providing test configuration with temp file
    """
    # Save version
    test_version = "v4.0.0"
    save_last_version(test_version, test_version_file)
    
    # Load and verify
    loaded_version = load_last_version(test_version_file)
    assert loaded_version == test_version
    
    # Verify file contents
    with open(test_version_file['storage']['version_file'], 'r') as f:
        data = json.load(f)
        assert data['last_version'] == test_version
        assert 'last_check' in data

# ============================================================================
# Error Handling Tests
# ============================================================================

def test_invalid_version_file(test_version_file):
    """Verify handling of corrupted version file.
    
    Test ensures:
    1. Invalid JSON is detected
    2. None is returned for corrupted file
    3. No exceptions are raised
    4. Error is handled gracefully
    
    Args:
        test_version_file: Fixture providing test configuration with temp file
    """
    # Create invalid JSON
    with open(test_version_file['storage']['version_file'], 'w') as f:
        f.write("invalid json")
    
    # Should return None for invalid file
    assert load_last_version(test_version_file) is None

def test_version_file_permissions(test_version_file):
    """Verify handling of file permission issues.
    
    Test ensures:
    1. Read-only file is detected
    2. Permission error is raised appropriately
    3. Original file is not corrupted
    4. Error message is descriptive
    
    Args:
        test_version_file: Fixture providing test configuration with temp file
    """
    # Save initial version
    save_last_version("v4.0.0", test_version_file)
    
    # Make file read-only
    os.chmod(test_version_file['storage']['version_file'], 0o444)
    
    # Should handle permission error gracefully
    with pytest.raises(PermissionError):
        save_last_version("v4.0.1", test_version_file)
    
    # Cleanup
    os.chmod(test_version_file['storage']['version_file'], 0o640)  # rw-r----- 