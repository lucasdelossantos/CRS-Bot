# CRS-Bot

CRS-Bot is a versatile tool that monitors GitHub releases and sends notifications to Discord. It can run both as a GitHub Action and as a standalone script, making it flexible for different use cases.

## Quick Start

### As a GitHub Action (Recommended)
1. Fork or create a new repository
2. Create a Discord webhook ([Discord webhook guide](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks))
3. Add the webhook URL as a repository secret:
   ```
   Name: DISCORD_WEBHOOK_URL
   Value: your-discord-webhook-url
   ```
4. Create `.github/workflows/check_release.yaml`:
   ```yaml
   name: Check Release
   on:
     schedule:
       - cron: '0 * * * *'  # Run hourly
     workflow_dispatch:      # Allow manual runs
   
   jobs:
     check:
       runs-on: ubuntu-latest
       steps:
         - uses: lucasdelossantos/CRS-Bot@main
           with:
             discord_webhook_url: ${{ secrets.DISCORD_WEBHOOK_URL }}
   ```
That's it! The bot will now check for new releases hourly and notify your Discord channel.

### As a Standalone Script
```bash
# Clone and setup
git clone https://github.com/lucasdelossantos/CRS-Bot.git
cd CRS-Bot
pip install -r requirements.txt

# Configure
export DISCORD_WEBHOOK_URL="your-discord-webhook-url"

# Run
python github_release.py
```

For more detailed setup options and configuration, see the [Setup](#setup) section below.

## Features

- Monitors the latest releases of a specified GitHub repository
- Sends notifications to a Discord channel when a new release is detected
- Keeps track of the last checked version to avoid duplicate notifications
- Configurable to monitor specific version patterns (e.g., versions 4.x and beyond)
- Discord webhook integration with rich embeds
- Automatic retry logic for API requests
- Detailed logging
- YAML-based configuration
- Runs both as a GitHub Action and standalone script

## Setup

### Prerequisites

- Python 3.x
- A Discord Webhook URL
- GitHub repository with appropriate permissions (for GitHub Actions)

### Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/lucasdelossantos/CRS-Bot.git
    cd CRS-Bot
    ```

2. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

3. Set up Discord webhook:

    #### For Local Development:
    ```bash
    export DISCORD_WEBHOOK_URL="your_discord_webhook_url"
    ```

    #### For GitHub Actions:
    1. Go to your repository on GitHub
    2. Navigate to Settings > Secrets and variables > Actions
    3. Add a new repository secret named `DISCORD_WEBHOOK_URL` with your webhook URL
    4. Note: GitHub token is automatically provided by GitHub Actions - no additional setup required

### Configuration

The bot can be configured by editing [`config.yaml`](config.yaml). The Discord webhook URL can be specified in three ways, in order of priority:
1. Environment variable `DISCORD_WEBHOOK_URL` (recommended for local development)
2. GitHub Actions secret (for GitHub Actions)
3. In the config.yaml file (convenient but less secure)

```yaml
# GitHub Configuration
github:
  repository: "coreruleset/coreruleset"  # The GitHub repository to monitor
  name: "Core Rule Set"                  # Display name for notifications
  version_pattern: "^v?[4-9]\\.*"       # Version pattern to monitor
  api:
    retries: 3                          # Number of API retry attempts
    backoff_factor: 1                   # Backoff factor between retries
    status_forcelist: [429, 500, 502, 503, 504]  # Status codes to retry on
    headers:
      accept: "application/vnd.github.v3+json"
      user_agent: "CRS-Bot"

# File Storage Configuration
storage:
  version_file: "last_version.json"     # File to store the last checked version

# Logging Configuration
logging:
  level: "INFO"                         # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  format: "%(asctime)s - %(levelname)s - %(message)s"
  file: "github_release_bot.log"        # Log file path

# Discord Configuration
discord:
  notification:
    color: 5814783                      # Embed color (decimal format)
    footer_text: "CRS-Bot"              # Footer text in notifications
    webhook_url: ""                     # Optional: Discord webhook URL (can be overridden by environment variable)
```

**Note:** While you can specify the webhook URL in the config file, it's recommended to use environment variables or GitHub secrets for better security, especially if your repository is public.

### Usage

#### Running as a GitHub Action

The repository includes a GitHub Actions workflow file at [`check_release.yaml`](.github/workflows/check_release.yaml) that handles automated release checking. This workflow:

- Runs automatically every hour (configurable in the workflow file)
- Can be triggered manually through the Actions tab
- Uses the webhook URL from repository secrets
- Uses the default `GITHUB_TOKEN` automatically provided by GitHub Actions

You can view and modify the workflow configuration in [`check_release.yaml`](.github/workflows/check_release.yaml). The workflow handles:

- Setting up Python
- Installing dependencies
- Running the release check script
- Managing repository permissions and secrets

No additional workflow setup is required - the necessary configuration is already included in the repository.

#### Running Locally

To run the bot manually:
```bash
python github_release.py
```

The bot will:
1. Check for new releases on GitHub
2. Compare against the last checked version
3. Send a Discord notification if a new version is detected
4. Save the latest version information

### Files

- [`github_release.py`](github_release.py): The main script that checks for new releases and sends notifications
- [`check_release.yaml`](.github/workflows/check_release.yaml): The GitHub Action workflow file
- [`config.yaml`](config.yaml): Configuration file for bot settings
- [`last_version.json`](last_version.json): A file that stores the last checked version
- [`requirements.txt`](requirements.txt): Python package dependencies
- [`LICENSE`](LICENSE): MIT License file

### License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes or improvements.

## Contact

For any questions or inquiries, please contact Lucas de los Santos.
