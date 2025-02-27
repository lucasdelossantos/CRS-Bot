import requests
import time
import json
import os
import re

github_repo = "coreruleset/coreruleset"  # Replace with actual GitHub repo (e.g., "torvalds/linux")
api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
github = "Core Rule Set"

# File to store the last checked version
VERSION_FILE = "last_version.json"

# Discord Webhook URL (Replace with your actual webhook URL)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Specify the version pattern to monitor (versions 4.x and beyond)
VERSION_PATTERN = re.compile(r"^v?[4-9]\..*")

def get_latest_release():
    print("Fetching latest release from GitHub...")
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        print(f"Latest release found: {data.get('tag_name')}")
        return data["tag_name"]  # GitHub uses 'tag_name' for releases
    except requests.RequestException as e:
        print(f"Error fetching release: {e}")
        return None

def load_last_version():
    print("Loading last recorded version...")
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as file:
            last_version = json.load(file).get("last_version")
            print(f"Last recorded version: {last_version}")
            return last_version
    print("No previous version recorded.")
    return None

def save_last_version(version):
    print(f"Saving new version: {version}")
    with open(VERSION_FILE, "w") as file:
        json.dump({"last_version": version}, file)

def send_discord_notification(version):
    print(f"Sending Discord notification for version: {version}")
    release_url = f"https://github.com/{github_repo}/releases/tag/{version}"
    message = {
        "content": f"New {github} release detected! Version: [{version}]({release_url})"
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=message)
        response.raise_for_status()
        print("Discord notification sent!")
    except requests.RequestException as e:
        print(f"Error sending Discord message: {e}")

def check_for_new_release():
    print("Checking for a new release...")
    latest_version = get_latest_release()
    if not latest_version:
        print("No release found or error occurred.")
        return
    
    if not VERSION_PATTERN.match(latest_version):
        print(f"Version {latest_version} does not match the monitored pattern.")
        return
    
    last_version = load_last_version()
    
    if last_version != latest_version:
        print(f"New release detected! Version: {latest_version}")
        send_discord_notification(latest_version)
        save_last_version(latest_version)
    else:
        print("No new release detected.")

if __name__ == "__main__":
    check_for_new_release()