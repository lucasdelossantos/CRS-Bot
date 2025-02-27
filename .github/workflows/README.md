# CRS-Bot

CRS-Bot is a GitHub Action that monitors the latest releases of a specified GitHub repository and sends notifications to a Discord channel when a new release is detected. The bot also keeps track of the last checked version to avoid duplicate notifications.

## Features

- Monitors the latest releases of a specified GitHub repository.
- Sends notifications to a Discord channel when a new release is detected.
- Keeps track of the last checked version to avoid duplicate notifications.
- Configurable to monitor specific version patterns (e.g., versions 4.x and beyond).

## Setup

### Prerequisites

- Python 3.x
- A Discord Webhook URL
- GitHub repository with appropriate permissions

### Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/lucasdelossantos/CRS-Bot.git
    cd CRS-Bot
    ```

2. Install the required Python packages:

    ```sh
    python -m pip install --upgrade pip
    pip install requests
    ```

3. Set up the Discord Webhook URL as a secret in your GitHub repository settings:

    - Go to your repository on GitHub.
    - Click on `Settings`.
    - Click on `Secrets and variables` > `Actions`.
    - Click on `New repository secret`.
    - Add a new secret with the name [DISCORD_WEBHOOK_URL](http://_vscodecontentref_/0) and paste your Discord Webhook URL as the value.

### Configuration

The main configuration file for the GitHub Action is located at [check_release.yaml](http://_vscodecontentref_/1). This file defines the schedule and steps for the action.

### Usage

The GitHub Action is set to run every hour by default. You can also manually trigger the action using the `workflow_dispatch` event.

### Files

- [github_release.py](http://_vscodecontentref_/2): The main script that checks for new releases and sends notifications.
- [check_release.yaml](http://_vscodecontentref_/3): The GitHub Action workflow file.
- [last_version.json](http://_vscodecontentref_/4): A file that stores the last checked version.

### License

This project is licensed under the MIT License. See the [LICENSE](http://_vscodecontentref_/5) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes or improvements.

## Contact

For any questions or inquiries, please contact Lucas de los Santos.
