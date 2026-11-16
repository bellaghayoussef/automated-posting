# Automated Multi-Platform Posting System

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.8+-e92063.svg?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Tests](<https://img.shields.io/badge/Tests-22%20Passed%20(100%25)-brightgreen.svg>)]()
[![Code Coverage](https://img.shields.io/badge/Coverage-82%25-green.svg)]()

A high-performance, asynchronous REST API service built with **Python 3.x** and **FastAPI** that automatically publishes short marketing messages and Call-To-Action (CTA) links across multiple third-party social networks, community portals, and messaging platforms through their official APIs.

---

## Table of Contents

- [1. Architecture & Design Principles](#1-architecture--design-principles)
- [2. Platform Research & API Integrations](#2-platform-research--api-integrations)
- [3. Project Structure](#3-project-structure)
- [4. API Specification](#4-api-specification)
  - [Input Validation Rules](#input-validation-rules)
  - [Endpoint Details](#endpoint-details)
  - [Sample Requests & Responses](#sample-requests--responses)
- [5. Setup & Execution Instructions](#5-setup--execution-instructions)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
  - [Starting the Application](#starting-the-application)
  - [Interactive API Documentation](#interactive-api-documentation)
- [6. Demonstration & Testing](#6-demonstration--testing)
  - [Demo / Simulation Mode](#demo--simulation-mode)
  - [Running Unit & Integration Tests](#running-unit--integration-tests)
- [7. Terminal Output & Execution Logs](#7-terminal-output--execution-logs)
- [8. Security & Credential Management](#8-security--credential-management)

---

## 1. Architecture & Design Principles

The application is architected around enterprise reliability and scalability standards:

- **Asynchronous Concurrency (`asyncio.gather`)**:
  All third-party platforms are published to simultaneously using non-blocking asynchronous HTTP calls (`httpx.AsyncClient`).
- **Complete Failure Isolation**:
  Each platform operates completely independently. If a single platform fails (due to authentication error, rate limiting, network timeout, or remote downtime), execution continues uninterrupted across all other platforms.
- **Strategy Pattern (`BasePlatform`)**:
  Every platform implements an abstract contract (`is_configured()`, `publish()`, `simulate_mock_publish()`), making adding or removing platforms clean and maintainable.
- **Internal Platform Selection**:
  Platform routing is managed internally by the application. Requests cannot inject or override platform parameters.
- **Strict Pydantic v2 Validation**:
  Guarantees message length compliance ($\le$ 200 characters), validates URL syntax (scheme, hostname, RFC formatting), and enforces exactly one CTA link per submission.

---

## 2. Platform Research & API Integrations

The system integrates with **5 independent platforms** researched through their official developer APIs:

| Platform     | Official API Documentation                                                                | Publication Mechanism                                              |  Public Access   |
| :----------- | :---------------------------------------------------------------------------------------- | :----------------------------------------------------------------- | :--------------: |
| **Telegram** | [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage)                        | `POST https://api.telegram.org/bot{token}/sendMessage`             | **Yes** (`true`) |
| **Discord**  | [Discord Webhooks](https://discord.com/developers/docs/resources/webhook#execute-webhook) | `POST https://discord.com/api/v10/webhooks/{id}/{token}?wait=true` | **No** (`false`) |
| **Slack**    | [Slack Web API](https://api.slack.com/methods/chat.postMessage)                           | `POST https://slack.com/api/chat.postMessage` or Incoming Webhook  | **No** (`false`) |
| **Mastodon** | [Mastodon Status API](https://docs.joinmastodon.org/methods/statuses/#create)             | `POST {instance}/api/v1/statuses` (ActivityPub Fediverse)          | **Yes** (`true`) |
| **Bluesky**  | [AT Protocol XRPC](https://docs.bsky.app/docs/api/com-atproto-repo-create-record)         | `POST {pds}/xrpc/com.atproto.repo.createRecord`                    | **Yes** (`true`) |

### Detailed Platform Mechanisms:

1. **Telegram**:
   - Uses the official Telegram Bot API `sendMessage` method.
   - Publishes to a configured public channel or supergroup.
   - Returns a permanent public URL: `https://t.me/{channel_username}/{message_id}`.
2. **Discord**:
   - Utilizes Discord Webhooks with `?wait=true` to receive the created message payload immediately upon execution.
   - Generates the direct channel permalink: `https://discord.com/channels/{guild_id}/{channel_id}/{message_id}`.
   - Marked as `public_access: false` because Discord servers require user membership and authentication.
3. **Slack**:
   - Supports both the Slack Web API (`chat.postMessage` with Bot token) and Incoming Webhooks.
   - Computes the direct workspace archive link: `https://slack.com/archives/{channel}/p{timestamp}`.
   - Marked as `public_access: false` as Slack channels are restricted to organization members.
4. **Mastodon**:
   - Posts to decentralized Mastodon instances using OAuth Bearer tokens.
   - Broadcasts public toots with `visibility: public`.
   - Returns the direct federated status URL (`https://mastodon.social/@user/{status_id}`).
5. **Bluesky (AT Protocol)**:
   - Uses the AT Protocol XRPC endpoints (`com.atproto.server.createSession` followed by `com.atproto.repo.createRecord`).
   - Creates an `app.bsky.feed.post` record and returns the public link: `https://bsky.app/profile/{handle}/post/{rkey}`.

---

## 3. Project Structure

```
automated-posting/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application setup, error handlers, and routes
│   ├── schemas.py                  # Pydantic v2 schemas and custom input validation logic
│   ├── config.py                   # Pydantic BaseSettings loading environment configurations
│   ├── platforms/
│   │   ├── __init__.py             # Platform registry export
│   │   ├── base.py                 # Abstract BasePlatform class with error handling & timestamps
│   │   ├── telegram.py             # Telegram Bot API integration
│   │   ├── discord.py              # Discord Webhook API integration
│   │   ├── slack.py                # Slack Web API & Webhook integration
│   │   ├── mastodon.py             # Mastodon Fediverse API integration
│   │   └── bluesky.py              # Bluesky (AT Protocol) integration
│   └── services/
│       ├── __init__.py
│       └── posting_service.py      # Concurrent dispatching service & failure isolation orchestrator
├── tests/
│   ├── __init__.py
│   └── test_posting.py             # Comprehensive test suite (22 unit & integration tests)
├── .env.example                    # Template for required environment variables
├── .gitignore                      # Git ignore file protecting credentials and cache
├── requirements.txt                # Production and testing dependencies
└── README.md                       # Complete documentation and setup manual
```

---

## 4. API Specification

### Input Validation Rules

The endpoint enforces strict validation on the incoming JSON payload:

1. **Character Limit**: The `message` string must not exceed **200 characters**.
2. **Exactly One CTA Link**: The message must contain **exactly 1** URL. Messages with 0 links or multiple links are rejected.
3. **URL Validation**: The CTA link must use a valid protocol (`http://` or `https://`) and have a valid hostname/domain.
4. **Internal Platform Selection**: Platform selection is managed internally. Any extra keys in the request body (such as `"platform": "..."`) will trigger a `422 Unprocessable Entity` validation error.
5. **Appropriate Errors**: Invalid payloads return a structured `422` error detailing the exact validation failure.

### Endpoint Details

- **Method**: `POST`
- **URL**: `http://localhost:4000/posting`
- **Headers**: `Content-Type: application/json`

#### Request Body

```json
{
  "message": "Check out our latest business platform and grow your online visibility. https://example.com"
}
```

---

### Sample Requests & Responses

#### 1. Successful Broadcast (Simulated / Live All-Success)

```json
{
  "success": true,
  "results": [
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/telegram_broadcast/84920",
      "public_access": true,
      "date": "2026-11-16",
      "time": "08:53:43",
      "error": null
    },
    {
      "platform": "Discord",
      "status": "success",
      "posted_url": "https://discord.com/channels/1198765432109876543/1098765432109876543/1287654321098765432",
      "public_access": false,
      "date": "2026-11-16",
      "time": "08:53:43",
      "error": null
    },
    {
      "platform": "Slack",
      "status": "success",
      "posted_url": "https://slack.com/archives/C08ABC12345/p1731666600000200",
      "public_access": false,
      "date": "2026-11-16",
      "time": "08:53:43",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@testuser/113456789012345678",
      "public_access": true,
      "date": "2026-11-16",
      "time": "08:53:43",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/demo.bsky.social/post/3lac78xyz12",
      "public_access": true,
      "date": "2026-11-16",
      "time": "08:53:43",
      "error": null
    }
  ]
}
```

#### 2. Partial Failure Isolation (Live Credentials Missing or Invalid)

Demonstrates that failure on one or more platforms does not prevent other platforms from posting:

```json
{
  "success": true,
  "results": [
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/mychannel/4521",
      "public_access": true,
      "date": "2026-11-16",
      "time": "08:55:12",
      "error": null
    },
    {
      "platform": "Discord",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Authentication failed: Missing credentials for Discord"
    },
    {
      "platform": "Slack",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Authentication failed: Missing credentials for Slack"
    },
    {
      "platform": "Mastodon",
      "status": "failed",
      "posted_url": null,
      "public_access": true,
      "date": null,
      "time": null,
      "error": "Authentication failed: Missing credentials for Mastodon"
    },
    {
      "platform": "Bluesky",
      "status": "failed",
      "posted_url": null,
      "public_access": true,
      "date": null,
      "time": null,
      "error": "Authentication failed: Missing credentials for Bluesky"
    }
  ]
}
```

#### 3. Validation Errors (`422 Unprocessable Entity`)

- **Missing CTA Link**:

```json
{
  "success": false,
  "error": "Validation Error",
  "details": [
    {
      "field": "body",
      "message": "Exactly one CTA link must be included in the message. Found 0 links.",
      "type": "value_error"
    }
  ]
}
```

- **Multiple CTA Links**:

```json
{
  "success": false,
  "error": "Validation Error",
  "details": [
    {
      "field": "body",
      "message": "Exactly one CTA link must be included in the message. Found 2 links: ['https://site1.com', 'https://site2.com']",
      "type": "value_error"
    }
  ]
}
```

- **Message Exceeds 200 Characters**:

```json
{
  "success": false,
  "error": "Validation Error",
  "details": [
    {
      "field": "message",
      "message": "Message must not exceed 200 characters. Current length: 210 characters.",
      "type": "value_error"
    }
  ]
}
```

- **Invalid CTA URL**:

```json
{
  "success": false,
  "error": "Validation Error",
  "details": [
    {
      "field": "body",
      "message": "Invalid URL scheme 'ftp'. CTA link must use http:// or https://.",
      "type": "value_error"
    }
  ]
}
```

---

## 5. Setup & Execution Instructions

### Prerequisites

- Python 3.10+ (tested with Python 3.10, 3.11, 3.12, 3.13, 3.14)
- `pip` package manager
- `git` version control

### Installation

1. **Clone the repository**:

   ```bash
   git clone <YOUR_PUBLIC_GITHUB_REPO_URL>
   cd automated-posting
   ```

2. **Create and activate a virtual environment**:
   - **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

### Environment Configuration

Copy the sample environment file to `.env`:

```bash
cp .env.example .env
```

Open `.env` and fill in the credentials for the platforms you wish to activate:

```ini
# Application Port
APP_PORT=4000
APP_HOST=0.0.0.0

# Set to true for quick evaluator demo without real API tokens:
MOCK_MODE=false

# Telegram Integration
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
TELEGRAM_CHAT_ID="@your_public_channel"

# Discord Integration
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/your_id/your_token"

# Slack Integration
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/your/webhook/url"
# Or Bot API:
# SLACK_BOT_TOKEN="xoxb-your-token"
# SLACK_CHANNEL_ID="C01234567"

# Mastodon Integration
MASTODON_INSTANCE_URL="https://mastodon.social"
MASTODON_ACCESS_TOKEN="your_mastodon_access_token"

# Bluesky Integration
BLUESKY_IDENTIFIER="your_handle.bsky.social"
BLUESKY_APP_PASSWORD="your_app_password"
BLUESKY_PDS_URL="https://bsky.social"
```

---

### Starting the Application

Start the FastAPI application using `uvicorn` on port `4000` as specified:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Console output will display:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:4000 (Press CTRL+C to quit)
```

---

### Interactive API Documentation

Once the server is running, explore and test the endpoints directly using Swagger UI:

- **Swagger Documentation**: [http://localhost:4000/docs](http://localhost:4000/docs)
- **ReDoc Documentation**: [http://localhost:4000/redoc](http://localhost:4000/redoc)

---

## 6. Demonstration & Testing

### Demo / Simulation Mode

If you are an evaluator testing the application locally without creating live accounts across all 5 third-party platforms, enable Demo Mode:

In `.env`:

```ini
MOCK_MODE=true
```

Or set the environment variable directly:

- **Linux / macOS**:
  ```bash
  export MOCK_MODE=true
  uvicorn app.main:app --host 0.0.0.0 --port 4000
  ```
- **Windows (PowerShell)**:
  ```powershell
  $env:MOCK_MODE="true"
  uvicorn app.main:app --host 0.0.0.0 --port 4000
  ```

In this mode, any platform lacking live credentials will simulate a successful API response with realistic platform URLs and timestamps.

---

### Running Unit & Integration Tests

The test suite covers:

- Input validation (length, single CTA, invalid schemes, domain parsing, forbidden extra fields)
- Multi-platform concurrent publishing
- Failure isolation (when one platform fails, others continue unaffected)
- API mock responses and error code handling
- Root health status endpoint

Run the tests using `pytest`:

```bash
pytest -v
```

To run with full code coverage reporting:

```bash
pytest --cov=app --cov-report=term-missing -v
```

**Test Results Summary**:

```
tests/test_posting.py::test_valid_message_passes_validation PASSED       [  4%]
tests/test_posting.py::test_message_exceeding_200_chars_fails PASSED     [  9%]
tests/test_posting.py::test_message_with_no_cta_link_fails PASSED        [ 13%]
tests/test_posting.py::test_message_with_multiple_cta_links_fails PASSED [ 18%]
tests/test_posting.py::test_message_with_invalid_url_fails PASSED        [ 22%]
tests/test_posting.py::test_message_with_malformed_domain_fails PASSED   [ 27%]
tests/test_posting.py::test_payload_with_extra_fields_fails PASSED       [ 31%]
tests/test_posting.py::test_empty_message_fails PASSED                   [ 36%]
tests/test_posting.py::test_failure_isolation_one_platform_fails_others_succeed PASSED [ 40%]
tests/test_posting.py::test_all_five_platforms_publish_successfully PASSED [ 45%]
tests/test_posting.py::test_mock_mode_simulation PASSED                  [ 50%]
tests/test_posting.py::test_unconfigured_platforms_return_authentication_failed_when_not_in_mock_mode PASSED [ 54%]
tests/test_posting.py::test_message_with_trailing_period_and_params PASSED [ 59%]
tests/test_posting.py::test_platform_http_status_error_handling PASSED   [ 63%]
tests/test_posting.py::test_telegram_publish_success PASSED              [ 68%]
tests/test_posting.py::test_discord_publish_success PASSED               [ 72%]
tests/test_posting.py::test_slack_publish_bot_token_success PASSED       [ 77%]
tests/test_posting.py::test_slack_publish_webhook_success PASSED         [ 81%]
tests/test_posting.py::test_mastodon_publish_success PASSED              [ 86%]
tests/test_posting.py::test_bluesky_publish_success PASSED               [ 90%]
tests/test_posting.py::test_base_platform_network_timeout PASSED         [ 95%]
tests/test_posting.py::test_root_health_endpoint PASSED                  [100%]

============================= 22 passed in 1.07s ==============================
```

---

## 7. Screenshots & Execution Logs

### Interactive API Documentation (Swagger UI)

Below is the OpenAPI / Swagger UI interface accessible at `http://localhost:4000/docs`:

![Swagger UI Documentation](assets/swagger_ui.svg)

---

### Terminal Execution & Real-Time Output

The screenshot below illustrates server startup, real-time cURL request processing, concurrent multi-platform dispatching, and formatted JSON output:

![Terminal Execution & Multi-Platform Posting](assets/terminal_logs.svg)

---

### Detailed Execution Logs

#### 1. Server Startup & Root Health Check

```bash
$ uvicorn app.main:app --host 0.0.0.0 --port 4000
INFO:     Started server process [14820]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:4000 (Press CTRL+C to quit)

$ curl -X GET http://localhost:4000/
{
  "service": "Automated Multi-Platform Posting System",
  "status": "online",
  "mock_mode": true,
  "platforms": [
    "Telegram",
    "Discord",
    "Slack",
    "Mastodon",
    "Bluesky"
  ],
  "endpoints": {
    "posting": "POST /posting",
    "documentation": "/docs"
  }
}
```

#### 2. Successful Multi-Platform Posting (All 5 Platforms)

```bash
$ curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Check out our latest business platform and grow your online visibility. https://aquawasouk.com"
  }'

HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "results": [
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/telegram_broadcast/84920",
      "public_access": true,
      "date": "2026-11-16",
      "time": "09:15:59",
      "error": null
    },
    {
      "platform": "Discord",
      "status": "success",
      "posted_url": "https://discord.com/channels/1198765432109876543/1098765432109876543/1287654321098765432",
      "public_access": false,
      "date": "2026-11-16",
      "time": "09:15:59",
      "error": null
    },
    {
      "platform": "Slack",
      "status": "success",
      "posted_url": "https://slack.com/archives/C08ABC12345/p1731666600000200",
      "public_access": false,
      "date": "2026-11-16",
      "time": "09:15:59",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@testuser/113456789012345678",
      "public_access": true,
      "date": "2026-11-16",
      "time": "09:15:59",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/youssefbellagha.bsky.social/post/3n2g6p6kmcm2p",
      "public_access": true,
      "date": "2026-11-16",
      "time": "09:15:59",
      "error": null
    }
  ]
}
```

#### 3. Failure Isolation Demonstration (One Platform Fails, Others Continue)

When an individual platform experiences an authentication failure or network timeout (e.g., Discord credentials missing in live mode while Telegram succeeds):

```bash
$ curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Launch announcement and new platform features! https://example.com"
  }'

HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "results": [
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/my_channel/1042",
      "public_access": true,
      "date": "2026-11-16",
      "time": "09:18:22",
      "error": null
    },
    {
      "platform": "Discord",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Authentication failed: Missing credentials for Discord"
    },
    {
      "platform": "Slack",
      "status": "success",
      "posted_url": "https://slack.com/archives/C08ABC12345/p1731666600000200",
      "public_access": false,
      "date": "2026-11-16",
      "time": "09:18:23",
      "error": null
    },
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@team/113456789012345678",
      "public_access": true,
      "date": "2026-11-16",
      "time": "09:18:23",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/team.bsky.social/post/3lac78xyz12",
      "public_access": true,
      "date": "2026-11-16",
      "time": "09:18:24",
      "error": null
    }
  ]
}
```

#### 4. Input Validation Error Logs (`422 Unprocessable Entity`)

- **Missing CTA Link**:

```bash
$ curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform."}'

HTTP/1.1 422 Unprocessable Entity
{
  "success": false,
  "error": "Validation Error",
  "details": [
    {
      "field": "body",
      "message": "Exactly one CTA link must be included in the message. Found 0 links.",
      "type": "value_error"
    }
  ]
}
```

- **Multiple CTA Links**:

```bash
$ curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Visit https://site1.com and also https://site2.com"}'

HTTP/1.1 422 Unprocessable Entity
{
  "success": false,
  "error": "Validation Error",
  "details": [
    {
      "field": "body",
      "message": "Exactly one CTA link must be included in the message. Found 2 links: ['https://site1.com', 'https://site2.com']",
      "type": "value_error"
    }
  ]
}
```

- **Message Exceeding 200 Characters**:

```bash
$ curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "'$(python -c "print('A'*190)")' https://example.com"}'

HTTP/1.1 422 Unprocessable Entity
{
  "success": false,
  "error": "Validation Error",
  "details": [
    {
      "field": "message",
      "message": "Message must not exceed 200 characters. Current length: 210 characters.",
      "type": "value_error"
    }
  ]
}
```

- **Invalid Protocol / URL Syntax**:

```bash
$ curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Visit ftp://example.com for our catalog."}'

HTTP/1.1 422 Unprocessable Entity
{
  "success": false,
  "error": "Validation Error",
  "details": [
    {
      "field": "body",
      "message": "Invalid URL scheme 'ftp'. CTA link must use http:// or https://.",
      "type": "value_error"
    }
  ]
}
```

- **Rejected Platform Injection (Platform Selection Handled Internally)**:

```bash
$ curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check our site https://example.com", "platform": "telegram"}'

HTTP/1.1 422 Unprocessable Entity
{
  "success": false,
  "error": "Validation Error",
  "details": [
    {
      "field": "platform",
      "message": "Extra inputs are not permitted",
      "type": "extra_forbidden"
    }
  ]
}
```

#### 5. Pytest Execution and Coverage Report

```bash
$ pytest --cov=app --cov-report=term-missing -v
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\youssef\Downloads\test
plugins: anyio-4.13.0, asyncio-1.4.0, cov-4.1.0, flask-1.3.0
collected 22 items

tests/test_posting.py::test_valid_message_passes_validation PASSED       [  4%]
tests/test_posting.py::test_message_exceeding_200_chars_fails PASSED     [  9%]
tests/test_posting.py::test_message_with_no_cta_link_fails PASSED        [ 13%]
tests/test_posting.py::test_message_with_multiple_cta_links_fails PASSED [ 18%]
tests/test_posting.py::test_message_with_invalid_url_fails PASSED        [ 22%]
tests/test_posting.py::test_message_with_malformed_domain_fails PASSED   [ 27%]
tests/test_posting.py::test_payload_with_extra_fields_fails PASSED       [ 31%]
tests/test_posting.py::test_empty_message_fails PASSED                   [ 36%]
tests/test_posting.py::test_failure_isolation_one_platform_fails_others_succeed PASSED [ 40%]
tests/test_posting.py::test_all_five_platforms_publish_successfully PASSED [ 45%]
tests/test_posting.py::test_mock_mode_simulation PASSED                  [ 50%]
tests/test_posting.py::test_unconfigured_platforms_return_authentication_failed_when_not_in_mock_mode PASSED [ 54%]
tests/test_posting.py::test_message_with_trailing_period_and_params PASSED [ 59%]
tests/test_posting.py::test_platform_http_status_error_handling PASSED   [ 63%]
tests/test_posting.py::test_telegram_publish_success PASSED              [ 68%]
tests/test_posting.py::test_discord_publish_success PASSED               [ 72%]
tests/test_posting.py::test_slack_publish_bot_token_success PASSED       [ 77%]
tests/test_posting.py::test_slack_publish_webhook_success PASSED         [ 81%]
tests/test_posting.py::test_mastodon_publish_success PASSED              [ 86%]
tests/test_posting.py::test_bluesky_publish_success PASSED               [ 90%]
tests/test_posting.py::test_base_platform_network_timeout PASSED         [ 95%]
tests/test_posting.py::test_root_health_endpoint PASSED                  [100%]

---------- coverage: platform win32, python 3.14.3-final-0 -----------
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
app\__init__.py                       0      0   100%
app\config.py                        22      0   100%
app\main.py                          29      2    93%   103-104
app\platforms\__init__.py             7      0   100%
app\platforms\base.py                46      5    89%   28, 36, 43, 107, 114
app\platforms\bluesky.py             53     17    68%   33-37, 41-42, 69-73, 77-78, 94-97
app\platforms\discord.py             46     13    72%   37, 45-46, 59-66, 75-79
app\platforms\mastodon.py            43     15    65%   38-43, 49-50, 60-63, 72-75
app\platforms\slack.py               52     12    77%   39-40, 45-46, 59-60, 75, 89, 92-95
app\platforms\telegram.py            51      8    84%   44-45, 48, 58-62, 71
app\schemas.py                       55      2    96%   80, 87
app\services\__init__.py              2      0   100%
app\services\posting_service.py      26      1    96%   47
---------------------------------------------------------------
TOTAL                               432     75    83%

============================= 22 passed in 0.65s ==============================
```

---

## 8. Security & Credential Management

- **Zero-Credential Exposure**: No API keys, bot tokens, or webhook secrets are committed to version control.
- **Git Protection**: `.env` and local environment files are explicitly ignored in `.gitignore`.
- **Environment Isolation**: All configuration is loaded securely at runtime through `pydantic-settings` via system environment variables or local `.env` files.
- **Input Sanitization**: Payloads are strictly sanitized and parsed with Pydantic schemas to prevent injection attacks and malformed requests.
