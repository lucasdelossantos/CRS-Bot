# CRS-Bot

[![GitHub Actions Status](https://github.com/lucasdelossantos/CRS-Bot/workflows/Tests/badge.svg)](https://github.com/lucasdelossantos/CRS-Bot/actions/workflows/test.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.x](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/downloads/)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=lucasdelossantos_CRS-Bot&metric=alert_status)](https://sonarcloud.io/dashboard?id=lucasdelossantos_CRS-Bot)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=lucasdelossantos_CRS-Bot&metric=security_rating)](https://sonarcloud.io/dashboard?id=lucasdelossantos_CRS-Bot)
[![CodeQL](https://github.com/lucasdelossantos/CRS-Bot/workflows/CodeQL/badge.svg)](https://github.com/lucasdelossantos/CRS-Bot/security/code-scanning)
[![Dependency Status](https://github.com/lucasdelossantos/CRS-Bot/actions/workflows/manual-dependabot.yml/badge.svg)](https://github.com/lucasdelossantos/CRS-Bot/actions/workflows/manual-dependabot.yml)

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

### As a Docker Container
```bash
# Clone the repository
git clone https://github.com/lucasdelossantos/CRS-Bot.git
cd CRS-Bot

# Create a .env file with your Discord webhook URL
echo "DISCORD_WEBHOOK_URL=your-discord-webhook-url" > .env

# Build and run with Docker Compose
docker compose up -d
```

Or using Docker directly:
```bash
# Build the image
docker build -t crs-bot .

# Run the container
docker run -d \
  -e DISCORD_WEBHOOK_URL=your-discord-webhook-url \
  -v $(pwd)/data:/app/data \
  --name crs-bot \
  crs-bot
```

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

### Personal Access Token (PAT) Maintenance

The repository uses a Personal Access Token (PAT) for creating dependency update pull requests. This token needs to be maintained:

1. **Token Expiration**: The PAT is set to expire every 90 days for security
2. **Required Permissions**:
   - `repo` (full control of private repositories)
   - `workflow` (to update workflow files)
3. **Token Rotation Process**:
   - GitHub will email you before the token expires
   - Generate a new token with the same permissions
   - Update the `PAT_TOKEN` secret in the repository
   - Delete the old token

To update the token:
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token
3. Go to repository → Settings → Secrets and variables → Actions
4. Update the `PAT_TOKEN` secret with the new token

### Docker Setup

The bot can be run as a Docker container, which provides several benefits:
- Consistent environment across different platforms
- Easy deployment and updates
- Isolated dependencies
- Built-in restart policies
- Multi-stage build with automated testing

#### Docker Build Stages

The Dockerfile includes three stages:
1. **Builder Stage**: Installs dependencies and builds the package
2. **Test Stage**: Runs unit tests with coverage reporting
3. **Final Stage**: Creates the production image

To build and test:
```bash
# Build and run tests
docker build --target test -t crs-bot-test .

# Build production image
docker build -t crs-bot .
```

#### Docker Compose (Recommended)
1. Clone the repository and navigate to it
2. Create a `.env` file with your Discord webhook URL:
   ```
   DISCORD_WEBHOOK_URL=your-discord-webhook-url
   ```
3. Start the container:
   ```bash
   docker compose up -d
   ```

#### Manual Docker Setup
1. Build the image:
   ```bash
   docker build -t crs-bot .
   ```
2. Run the container:
   ```bash
   docker run -d \
     -e DISCORD_WEBHOOK_URL=your-discord-webhook-url \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/logs:/app/logs \
     --name crs-bot \
     crs-bot
   ```

#### Docker Volumes
The container uses two Docker volumes for persistent storage:
- `/app/data`: Stores the `last_version.json` file
- `/app/logs`: Stores application logs

When running manually, these are typically mounted as:
- `./data:/app/data`
- `./logs:/app/logs`

#### Environment Variables
When running with Docker, configure the bot using environment variables:
- `DISCORD_WEBHOOK_URL`: Your Discord webhook URL (required)
- `DOCKER_CONTAINER`: Set to 1 (automatically set in container)
- Additional variables can be added in the `.env` file or docker-compose.yml

#### Health Check
The container includes a health check that monitors the application's ability to connect to GitHub's API:
```bash
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('https://api.github.com/zen', timeout=5)" || exit 1
```

#### Security Features
The container runs with several security best practices:
- Non-root user (`crsbot`)
- Minimal base image (python:3.11-slim)
- No unnecessary packages
- Read-only filesystem where possible
- Proper file permissions

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

### Testing

The project includes comprehensive tests that can be run in multiple ways:

#### Running Tests Locally
```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests with coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

#### Running Tests in Docker
The Dockerfile includes a dedicated test stage that runs tests during the build process:
```bash
# Build and run tests
docker build --target test -t crs-bot-test .
```

This will:
1. Build the application
2. Install test dependencies
3. Run all tests with coverage reporting
4. Fail the build if any tests fail

#### Test Environment
Tests run in a controlled environment with:
- Mocked Discord webhook responses
- Test-specific configuration
- Isolated file system
- Coverage reporting

#### Test Coverage
The test suite includes:
- Unit tests for core functionality
- Integration tests for GitHub API interaction
- Mock tests for Discord notifications
- Configuration validation tests
- Logging setup tests

Current coverage can be viewed in the test output or by running:
```bash
python -m pytest tests/ --cov=. --cov-report=html
```
