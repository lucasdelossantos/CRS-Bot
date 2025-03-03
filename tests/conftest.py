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
import logging
import yaml

def setup_test_logging():
    """Configure logging for tests."""
    # Create test config
    config = {
        'logging': {
            'file': 'data/github_release_bot.log',
            'level': 'DEBUG',
            'format': '%(asctime)s - %(levelname)s - %(message)s'
        }
    }
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Create log file
    log_file = os.path.join('data', 'github_release_bot.log')
    with open(log_file, 'a') as f:
        pass
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Setup test environment before any tests run."""
    # Setup logging first
    setup_test_logging()
    
    # Setup test environment variables
    os.environ['TEST_ENV'] = 'true'
    
    yield
    
    # Cleanup
    if 'TEST_ENV' in os.environ:
        del os.environ['TEST_ENV']

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