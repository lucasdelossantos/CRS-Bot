"""Shared pytest fixtures for all tests.

This module contains fixtures that are automatically available to all test files.
"""
import os
import shutil
import pytest
import json
import yaml
import tempfile
from pathlib import Path


@pytest.fixture(autouse=True)
def ensure_data_directory():
    """Ensure the data directory exists before each test.
    
    This fixture:
    1. Creates the data directory if it doesn't exist
    2. Creates required files (log file, etc.)
    3. Runs automatically for all tests (autouse=True)
    4. Cleans up the directory after each test
    """
    # Get data directory path
    data_dir = os.path.join(os.getcwd(), 'data')
    
    # Create empty log file if it doesn't exist
    log_file = os.path.join(data_dir, 'github_release_bot.log')
    if not os.path.exists(log_file):
        with open(log_file, 'a') as f:
            pass
    
    # Create empty version file if it doesn't exist
    version_file = os.path.join(data_dir, 'last_version.json')
    if not os.path.exists(version_file):
        with open(version_file, 'w') as f:
            f.write('{}')
    
    # Run the test
    yield
    
    # Clean up - remove all files in data directory but keep the directory
    for file_name in os.listdir(data_dir):
        file_path = os.path.join(data_dir, file_name)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Error cleaning up {file_path}: {e}')


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ['TEST_ENV'] = 'true'
    yield
    if 'TEST_ENV' in os.environ:
        del os.environ['TEST_ENV'] 