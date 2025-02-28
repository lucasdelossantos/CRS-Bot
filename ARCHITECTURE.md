# CRS-Bot Architecture

This document describes the architecture and design of CRS-Bot, explaining its components, data flow, and key design decisions.

## System Overview

CRS-Bot follows a simple, modular architecture designed for reliability and extensibility. The system consists of the following main components:

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  GitHub API     │ ←── │   CRS-Bot    │ ──→ │   Discord   │
│  (Data Source)  │     │   (Core)     │     │  (Notifier) │
└─────────────────┘     └──────────────┘     └─────────────┘
                             ↑    ↓
                        ┌────────────────┐
                        │  Local Storage │
                        │(Version Track) │
                        └────────────────┘
```

## Core Components

### 1. GitHub Release Monitor
- **Purpose**: Fetches and processes release information from GitHub
- **Key Features**:
  - Configurable repository monitoring
  - Version pattern matching
  - Rate limit handling
  - Automatic retries with exponential backoff
- **Implementation**: Uses GitHub's REST API v3 with requests library

### 2. Version Tracker
- **Purpose**: Maintains state of last checked version
- **Implementation**: JSON-based persistent storage
- **File**: `last_version.json`
- **Data Model**:
  ```json
  {
    "last_version": "string",
    "last_check": "ISO-8601 timestamp"
  }
  ```

### 3. Discord Notifier
- **Purpose**: Sends formatted notifications to Discord
- **Features**:
  - Rich embeds for better presentation
  - Configurable message formatting
  - Error handling and retries
- **Implementation**: Discord Webhook API

### 4. Configuration Manager
- **Purpose**: Manages application settings
- **Implementation**: YAML-based configuration
- **File**: `config.yaml`
- **Hierarchy**:
  1. Environment variables (highest priority)
  2. GitHub Actions secrets
  3. Configuration file (lowest priority)

## Data Flow

1. **Release Check Process**:
   ```
   Start
   ├─→ Load Configuration
   ├─→ Fetch Last Version
   ├─→ Query GitHub API
   ├─→ Compare Versions
   ├─→ [If New] Send Discord Notification
   └─→ Update Last Version
   ```

2. **Error Handling Flow**:
   ```
   Error Occurs
   ├─→ Retry Logic (if applicable)
   ├─→ Error Logging
   └─→ Graceful Degradation
   ```

## Design Decisions

### 1. Stateless Operation
- The bot maintains minimal state (only last version)
- Enables easy scaling and deployment
- Simplifies error recovery

### 2. Configuration Priority
- Environment variables take precedence
- Enables secure credential management
- Allows for easy deployment configuration

### 3. Modular Design
- Separate components for different responsibilities
- Easy to extend with new features
- Simple to maintain and test

### 4. Error Handling
- Comprehensive retry logic
- Detailed logging
- Graceful degradation

## Deployment Models

### 1. GitHub Action
```
┌─────────────────┐
│ GitHub Actions  │
├─────────────────┤
│ - Scheduled runs│
│ - Manual runs   │
│ - Auto-config   │
└─────────────────┘
```

### 2. Standalone Script
```
┌─────────────────┐
│ Local/Server    │
├─────────────────┤
│ - Manual runs   │
│ - Cron jobs     │
│ - Custom config │
└─────────────────┘
```

## Security Considerations

1. **API Authentication**
   - GitHub token management
   - Discord webhook URL protection
   - Environment variable usage

2. **Rate Limiting**
   - GitHub API rate limit handling
   - Discord rate limit compliance
   - Exponential backoff

3. **Error Prevention**
   - Input validation
   - Configuration validation
   - Type checking

## Future Architecture Considerations

1. **Scalability**
   - Multiple repository support
   - Additional notification channels
   - Webhook server mode

2. **Monitoring**
   - Prometheus metrics
   - Health checks
   - Status dashboard

3. **Integration**
   - Plugin system
   - API endpoints
   - Event system

## Development Guidelines

1. **Code Organization**
   - Modular components
   - Clear separation of concerns
   - Type hints and documentation

2. **Testing Strategy**
   - Unit tests for components
   - Integration tests for flows
   - Mocked external services

3. **Logging**
   - Structured logging
   - Different log levels
   - Audit trail 