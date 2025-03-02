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
    2. Runs automatically for all tests (autouse=True)
    3. Cleans up the directory after each test
    """
    # Create data directory
    data_dir = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
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