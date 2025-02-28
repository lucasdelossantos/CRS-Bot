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

def load_config() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {e}")

def get_discord_webhook_url() -> Optional[str]:
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
    webhook_url = config.get('discord', {}).get('notification', {}).get('webhook_url')
    if webhook_url:
        logger.debug("Using Discord webhook URL from config file")
        return webhook_url
    
    return None

# Load configuration
config = load_config()

# Configure logging
logging.basicConfig(
    level=getattr(logging, config['logging']['level']),
    format=config['logging']['format'],
    handlers=[
        logging.FileHandler(config['logging']['file']),
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

# Discord Webhook URL
DISCORD_WEBHOOK_URL = get_discord_webhook_url()
if not DISCORD_WEBHOOK_URL:
    logger.error("Discord webhook URL not found in environment variables or GitHub Actions secrets!")
    raise ValueError("Discord webhook URL is required (set DISCORD_WEBHOOK_URL environment variable or configure in GitHub Actions)")

# Version pattern
VERSION_PATTERN = re.compile(config['github']['version_pattern'])

def create_github_session():
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

def get_latest_release():
    """Fetch the latest release from GitHub."""
    logger.info("Fetching latest release from GitHub...")
    try:
        session = create_github_session()
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

def load_last_version():
    """Load the last recorded version from the version file."""
    logger.info("Loading last recorded version...")
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r") as file:
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

def save_last_version(version):
    """Save the latest version to the version file."""
    logger.info(f"Saving new version: {version}")
    with open(VERSION_FILE, "w") as file:
        json.dump({
            "last_version": version,
            "last_check": datetime.now().isoformat()
        }, file)

def send_discord_notification(version):
    """Send a notification to Discord about a new release."""
    logger.info(f"Sending Discord notification for version: {version}")
    release_url = f"https://github.com/{github_repo}/releases/tag/{version}"
    message = {
        "embeds": [{
            "title": f"New {github} Release!",
            "description": f"Version [{version}]({release_url}) has been released.",
            "color": config['discord']['notification']['color'],
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": config['discord']['notification']['footer_text']
            }
        }]
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=message)
        response.raise_for_status()
        logger.info("Discord notification sent successfully!")
    except requests.RequestException as e:
        logger.error(f"Error sending Discord message: {e}")
        response = getattr(e, 'response', None)
        if response:
            logger.error(f"Discord API response: {response.text}")

def check_for_new_release():
    """Check for new releases and send notifications if found."""
    logger.info("Starting new release check...")
    latest_version = get_latest_release()
    if not latest_version:
        logger.warning("No release found or error occurred.")
        return
    
    if not VERSION_PATTERN.match(latest_version):
        logger.info(f"Version {latest_version} does not match the monitored pattern.")
        return
    
    last_version = load_last_version()
    
    if last_version != latest_version:
        logger.info(f"New release detected! Version: {latest_version}")
        send_discord_notification(latest_version)
        save_last_version(latest_version)
    else:
        logger.info("No new release detected.")

if __name__ == "__main__":
    try:
        check_for_new_release()
    except Exception as e:
        logger.exception("Unexpected error occurred:")