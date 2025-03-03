import requests
import time
import json
import os
import re
import logging
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from typing import Dict, Any, Optional
import sys

def load_config() -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    The configuration file path is determined in the following order:
    1. CONFIG_PATH environment variable
    2. config.yaml in the same directory as the script
    """
    # Try environment variable first
    config_path = os.getenv('CONFIG_PATH')
    if not config_path:
        # Fall back to default path
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration from {config_path}: {e}")

def get_discord_webhook_url(config: Dict[str, Any] = None) -> Optional[str]:
    """
    Get Discord webhook URL from config or environment variables.
    Priority order:
    1. DISCORD_WEBHOOK_URL environment variable (local development)
    2. INPUT_DISCORD_WEBHOOK_URL environment variable (GitHub Actions)
    3. webhook_url from config.yaml
    """
    # Check for direct environment variable (local development)
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if webhook_url:
        logger.debug("Using Discord webhook URL from environment variable")
        return webhook_url
    
    # Check for GitHub Actions secret
    webhook_url = os.getenv("INPUT_DISCORD_WEBHOOK_URL")
    if webhook_url:
        logger.debug("Using Discord webhook URL from GitHub Actions secret")
        return webhook_url
    
    # Check config file
    if config:
        webhook_url = config.get('discord', {}).get('notification', {}).get('webhook_url')
        if webhook_url:
            logger.debug("Using Discord webhook URL from config file")
            return webhook_url
    
    return None

# Load configuration
config = load_config()

# Configure logging
log_file = config['logging']['file']
if not os.path.isabs(log_file):
    # If the path is relative, make it absolute relative to /app
    log_file = os.path.join('/app', log_file)

if not os.path.exists(log_file):
    raise RuntimeError(f"Log file {log_file} does not exist. Please create it with appropriate permissions.")

logging.basicConfig(
    level=getattr(logging, config['logging']['level']),
    format=config['logging']['format'],
    handlers=[
        logging.FileHandler(log_file, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# GitHub configuration
github_repo = config['github']['repository']
api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
github = config['github']['name']

# File to store the last checked version
VERSION_FILE = config['storage']['version_file']

# Discord Webhook URL - defer validation to function calls
DISCORD_WEBHOOK_URL = get_discord_webhook_url(config)

# Version pattern
VERSION_PATTERN = re.compile(config['github']['version_pattern'])

def create_github_session(config: Dict[str, Any]) -> requests.Session:
    """
    Create and configure a GitHub API session with retry logic.
    Note: GitHub token is only needed/used in GitHub Actions environment,
    where it's automatically provided by the Actions runner.
    """
    session = requests.Session()
    retries = Retry(
        total=config['github']['api']['retries'],
        backoff_factor=config['github']['api']['backoff_factor'],
        status_forcelist=config['github']['api']['status_forcelist']
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    # Add GitHub API headers
    session.headers.update({
        'Accept': config['github']['api']['headers']['accept'],
        'User-Agent': config['github']['api']['headers']['user_agent']
    })
    
    # In GitHub Actions, GITHUB_TOKEN is automatically available and should be used
    if 'GITHUB_ACTIONS' in os.environ:
        github_token = os.getenv('GITHUB_TOKEN')
        if github_token:
            session.headers['Authorization'] = f'token {github_token}'
    
    return session

def get_latest_release(config: Dict[str, Any] = None) -> Optional[str]:
    """Fetch the latest release from GitHub."""
    if not config:
        config = load_config()
    
    logger.info("Fetching latest release from GitHub...")
    try:
        session = create_github_session(config)
        github_repo = config['github']['repository']
        api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
        
        response = session.get(api_url)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Latest release found: {data.get('tag_name')}")
        return data["tag_name"]
    except requests.RequestException as e:
        logger.error(f"Error fetching release: {e}")
        response = getattr(e, 'response', None)
        if response:
            logger.error(f"Response status code: {response.status_code}")
            logger.error(f"Response body: {response.text}")
        return None

def load_last_version(config: Dict[str, Any] = None) -> Optional[str]:
    """
    Load the last recorded version from the version file.
    
    Args:
        config: Configuration dictionary containing storage settings
    """
    if not config:
        config = load_config()
    
    version_file = config['storage']['version_file']
    logger.info("Loading last recorded version...")
    
    if os.path.exists(version_file):
        try:
            with open(version_file, "r") as file:
                data = json.load(file)
                last_version = data.get("last_version")
                last_check = data.get("last_check")
                logger.info(f"Last recorded version: {last_version} (checked at: {last_check})")
                return last_version
        except json.JSONDecodeError as e:
            logger.error(f"Error reading version file: {e}")
            return None
    logger.info("No previous version recorded.")
    return None

def save_last_version(version: str, config: Dict[str, Any] = None) -> None:
    """
    Save the latest version to the version file.
    
    Args:
        version: Version string to save
        config: Configuration dictionary containing storage settings
    """
    if not config:
        config = load_config()
    
    version_file = config['storage']['version_file']
    logger.info(f"Saving new version: {version}")
    
    with open(version_file, "w") as file:
        json.dump({
            "last_version": version,
            "last_check": datetime.now().isoformat()
        }, file)

def send_discord_notification(version: str, config: Dict[str, Any] = None) -> bool:
    """
    Send a notification to Discord about a new release.
    
    Args:
        version: Version string to include in notification
        config: Configuration dictionary containing Discord settings
    
    Returns:
        bool: True if notification was sent successfully, False otherwise
    
    Raises:
        ValueError: If webhook URL is missing or version is None
        requests.RequestException: If the webhook request fails (unless in test environment)
    """
    if not config:
        config = load_config()
    
    if version is None:
        raise ValueError("Version string cannot be None")
    
    webhook_url = get_discord_webhook_url(config)
    if not webhook_url:
        raise ValueError("Discord webhook URL is required")
    
    # Check if we're in a test environment
    is_test_env = os.getenv('TEST_ENV') == 'true'
    if is_test_env:
        logger.info("Running in test environment - Discord notification errors will be non-fatal")
    
    logger.info(f"Sending Discord notification for version: {version}")
    github_repo = config['github']['repository']
    github_name = config['github']['name']
    release_url = f"https://github.com/{github_repo}/releases/tag/{version}"
    
    # Get color with default value
    try:
        color = config['discord']['notification']['color']
    except (KeyError, TypeError):
        logger.info("Using default color (blue) for Discord notification")
        color = 5814783  # Default blue color
    
    # Get footer text with default value
    try:
        footer_text = config['discord']['notification']['footer_text']
    except (KeyError, TypeError):
        logger.info("Using default footer text for Discord notification")
        footer_text = "GitHub Release Bot"
    
    message = {
        "embeds": [{
            "title": f"New {github_name} Release!",
            "description": f"Version [{version}]({release_url}) has been released.",
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": footer_text
            }
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=message)
        if response.status_code == 405 and is_test_env:
            logger.info("Received expected 405 error from test webhook - this is normal in test environment")
            return True
        response.raise_for_status()
        logger.info("Discord notification sent successfully")
        return True
    except requests.RequestException as e:
        logger.error(f"HTTP error sending Discord message: {e}")
        if not is_test_env:
            logger.error("Unexpected error occurred:")
            raise
        logger.warning("Ignoring Discord webhook error in test environment")
        return False

def check_for_new_release(config: Dict[str, Any] = None) -> None:
    """Check for new releases and send notifications if found."""
    if not config:
        config = load_config()
    
    logger.info("Starting new release check...")
    latest_version = get_latest_release(config)
    if not latest_version:
        logger.warning("No release found or error occurred.")
        return
    
    version_pattern = re.compile(config['github']['version_pattern'])
    if not version_pattern.match(latest_version):
        logger.info(f"Version {latest_version} does not match the monitored pattern.")
        return
    
    last_version = load_last_version(config)
    
    if last_version != latest_version:
        logger.info(f"New release detected! Version: {latest_version}")
        send_discord_notification(latest_version, config)
        save_last_version(latest_version, config)
    else:
        logger.info("No new release detected.")

if __name__ == "__main__":
    try:
        # Validate webhook URL before proceeding
        if not DISCORD_WEBHOOK_URL:
            logger.error("No Discord webhook URL configured! Please set DISCORD_WEBHOOK_URL environment variable, configure in GitHub Actions, or set in config file.")
            sys.exit(1)
        
        check_for_new_release()
    except Exception as e:
        logger.exception("Unexpected error occurred:")