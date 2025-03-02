"""Shared pytest fixtures for all tests.

This module contains fixtures that are automatically available to all test files.
"""
import os
import shutil
import pytest


@pytest.fixture(autouse=True)
def ensure_data_directory():
    """Ensure the data directory exists before each test.
    
    This fixture:
    1. Creates the data directory if it doesn't exist
    2. Creates required files (log file, etc.)
    3. Runs automatically for all tests (autouse=True)
    4. Cleans up the directory after each test
    """
    # Create data directory
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Create empty log file
    log_file = os.path.join(data_dir, 'github_release_bot.log')
    open(log_file, 'a').close()  # Create or touch the file
    
    # Create empty version file
    version_file = os.path.join(data_dir, 'last_version.json')
    if not os.path.exists(version_file):
        with open(version_file, 'w') as f:
            f.write('{}')
    
    # Ensure proper permissions
    os.chmod(data_dir, 0o700)  # rwx------
    os.chmod(log_file, 0o600)  # rw-------
    os.chmod(version_file, 0o600)  # rw-------
    
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