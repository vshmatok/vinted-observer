# Vinted Telegram Bot

Async Telegram bot that monitors Vinted marketplace listings and sends real-time notifications when new items matching your search criteria are found.

## Features

- **22 Vinted regions** — supports all major Vinted domains (PL, FR, DE, UK, ES, IT, and more)
- **Real-time monitoring** — configurable polling interval for near-instant notifications
- **Price filtering** — set minimum and maximum price per search
- **Proxy rotation** — least-recently-used strategy with health tracking and automatic ban recovery
- **SQLite with WAL mode** — concurrent reads, automatic cleanup of stale listings
- **CQRS architecture** — event-driven message bus with commands, queries, and events
- **Auto-migrations** — database schema applied automatically on startup via yoyo-migrations
- **Docker support** — multi-stage build with non-root user

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and main menu |
| `/add_search` | Create a new search with query and price filters |
| `/my_searches` | List, edit, or delete your saved searches |
| `/start_searching` | Start monitoring all your searches |
| `/stop_searching` | Pause monitoring |
| `/status` | Bot status, active searches, recent items, and errors |

## Tech Stack

- **Python 3.13+**
- **aiogram** — async Telegram Bot framework
- **aiohttp** — async HTTP client for Vinted API
- **aiosqlite** — async SQLite driver
- **yoyo-migrations** — database migration tool
- **uv** — package manager

## Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Telegram bot token from [BotFather](https://t.me/BotFather)
- (Recommended) One or more HTTP proxies

## Configuration

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

### Telegram

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### Vinted Domain

Set the Vinted region to monitor. Supported domains:

| Code | Country | Code | Country |
|---|---|---|---|
| `PL` | Poland | `IT` | Italy |
| `FR` | France | `LT` | Lithuania |
| `DE` | Germany | `LU` | Luxembourg |
| `CO_UK` | United Kingdom | `NL` | Netherlands |
| `ES` | Spain | `PT` | Portugal |
| `AT` | Austria | `RO` | Romania |
| `BE` | Belgium | `SE` | Sweden |
| `CZ` | Czech Republic | `SK` | Slovakia |
| `DK` | Denmark | `FI` | Finland |
| `GR` | Greece | `HR` | Croatia |
| `HU` | Hungary | `COM` | International |

```env
VINTED_DOMAIN=PL
```

### Database

```env
DATABASE_PATH=database.db
DB_CLEANUP_INTERVAL_HOURS=24
DB_LISTING_RETENTION_DAYS=1
DB_BUSY_TIMEOUT=5000
```

- `DB_BUSY_TIMEOUT` — SQLite busy timeout in milliseconds. 5000 ms is recommended for concurrent operations with WAL mode.

### Logging

```env
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_DATE_FORMAT=%Y-%m-%d %H:%M:%S
LOG_FILE=logs/app.log
```

> Do not remove `%(levelname)s` from the format — the `/status` command error parser relies on it.

### Status Command

```env
STATUS_ITEMS_TIMEFRAME_HOURS=1
ERROR_FETCH_AMOUNT=10
ERROR_LOG_LEVELS=ERROR,CRITICAL
```

### Search Polling

```env
SEARCH_SLEEP_TIME=1
```

See [Rate Limiting & Performance Tuning](#rate-limiting--performance-tuning) for details.

## Proxy Configuration

Proxies are configured via a JSON file (default: `src/resources/proxies.json`). Set the path in `.env`:

```env
PROXY_CONFIG_PATH=src/resources/proxies.json
```

### JSON Structure

```json
[
  {
    "ip": "64.137.96.74",
    "port": "6641",
    "username": "myuser",
    "password": "mypass",
    "is_https": false
  }
]
```

| Field | Type | Description |
|---|---|---|
| `ip` | string | Proxy server IP address |
| `port` | string | Proxy server port |
| `username` | string or null | Authentication username (optional) |
| `password` | string or null | Authentication password (optional) |
| `is_https` | boolean | Use HTTPS scheme if `true`, HTTP if `false` |

### Rotation Strategy

The proxy manager uses a **least-recently-used** strategy:

1. Each request picks the proxy that hasn't been used the longest.
2. On success, the proxy is marked healthy and rotated to the back of the queue.
3. On 401/429 responses, the proxy is marked as banned.
4. If all proxies are banned, the manager auto-resets and retries from the beginning.

### Why Proxies Matter

Vinted aggressively rate-limits and IP-bans repeated API requests. Without proxies, your bot's IP will get blocked quickly. For best results, use **1 proxy per active search**.

## Rate Limiting & Performance Tuning

`SEARCH_SLEEP_TIME` controls the delay (in seconds) between polling iterations per search task.

**Formula:**

```
effective_interval = SEARCH_SLEEP_TIME * (searches / proxies)
```

**Examples:**

| Proxies | Searches | Sleep Time | Effective Interval |
|---|---|---|---|
| 1 | 1 | 1s | ~1s |
| 1 | 5 | 1s | ~5s |
| 5 | 5 | 1s | ~1s |
| 3 | 10 | 1s | ~3.3s |

### Retry Logic

When the Vinted API returns 401 (Unauthorized) or 429 (Too Many Requests):

1. The client waits `2^retry` seconds (exponential backoff: 1s, 2s, 4s).
2. The failing proxy is marked as banned and a fresh proxy is selected.
3. Session cookie and user agent are refreshed.
4. After 3 failed retries, the request raises an error.

### Advice

Add more proxies rather than increasing `SEARCH_SLEEP_TIME`. The bot is designed for near-instant notifications — increasing the delay defeats the purpose.

## Deployment — Local

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run the bot
python main.py
```

## Deployment — Docker

The Dockerfile uses a multi-stage build: the first stage installs dependencies with `uv`, and the second stage runs as a non-root user (`appuser`).

### 1. Enable Docker overrides in `.env`

Uncomment the Docker paths at the bottom of your `.env`:

```env
DATABASE_PATH=/app/data/database.db
LOG_FILE=/app/logs/app.log
```

### 2. Build and run

```bash
# Start in detached mode
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Volumes

The `docker-compose.yml` defines two named volumes:

| Volume | Container Path | Purpose |
|---|---|---|
| `bot-data` | `/app/data` | SQLite database |
| `bot-logs` | `/app/logs` | Log files |

## Database & Migrations

### Automatic Migrations

Migrations are applied automatically on every startup before the bot begins polling. No manual steps are required for normal usage.

### yoyo-migrations

This project uses [yoyo-migrations](https://ollycope.com/software/yoyo/latest/) for schema management. Configuration lives in `pyproject.toml`:

```toml
[tool.yoyo]
batch_mode = "on"
migration_table = "_yoyo_migration"
sources = "./src/migrations"
```

### Existing Migrations

| File | Description |
|---|---|
| `001_create_searches_table.py` | Creates `searches` table (id, chat_id, query, price_min, price_max, timestamps) |
| `002_create_search_listings_table.py` | Creates `search_listings` table with foreign key to searches |
| `003_create_search_listings_index.py` | Adds index on `(search_id, created_at DESC)` for query performance |

### Creating New Migrations

Migration files live in `src/migrations/`. Each file uses yoyo's `step()` function with `apply` and `rollback` SQL:

```python
from yoyo import step

steps = [
    step(
        "CREATE TABLE example (id INTEGER PRIMARY KEY)",
        "DROP TABLE example"
    )
]
```

Name files with a sequential prefix: `004_description.py`, `005_description.py`, etc.

## Project Structure

```
vinted-telegram-bot/
├── main.py                          # Application entry point
├── pyproject.toml                   # Project config, dependencies, tool settings
├── Dockerfile                       # Multi-stage Docker build
├── docker-compose.yml               # Docker Compose services
├── .env.example                     # Environment variable template
│
├── src/
│   ├── config.py                    # Configuration from environment variables
│   ├── logger.py                    # Logging setup
│   │
│   ├── message_bus/                 # CQRS message bus
│   │   ├── message_bus.py           # Event/command/query dispatcher
│   │   ├── commands/                # Write operations (add, delete, update)
│   │   ├── events/                  # Domain events (item found, search lifecycle)
│   │   └── queries/                 # Read operations (get searches, filter listings)
│   │
│   ├── migrations/                  # yoyo database migrations
│   │
│   ├── monitoring/                  # Status reporting and error parsing
│   │
│   ├── repository/                  # Database access layer and migration runner
│   │
│   ├── search_processor/            # Search task management and execution loop
│   │
│   ├── telegram_bot/                # Bot setup, routers, FSM states, validators
│   │   ├── bot.py                   # Main bot class
│   │   ├── routers/                 # Command handlers (/start, /add_search, etc.)
│   │   ├── models/                  # Data models (Search)
│   │   ├── states/                  # FSM states for multi-step interactions
│   │   └── utility/                 # Keyboards, message builders, validators
│   │
│   ├── vinted_network_client/       # Vinted API client
│   │   ├── vinted_network_client.py # HTTP client with retry logic
│   │   ├── models/                  # Domain, item, proxy, price models
│   │   ├── exceptions/              # Custom exception hierarchy
│   │   └── utils/                   # Proxy manager, constants, middlewares
│   │
│   └── resources/                   # Static config files
│       ├── proxies.json             # Proxy list
│       └── agents.json              # User agent rotation list
│
└── tests/                           # Mirrors src/ structure
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov --cov-report=html

# Run a specific test file
uv run pytest tests/test_vinted_network_client/test_vinted_network_client.py
```

Coverage configuration excludes `src/migrations/` and `src/config.py` (see `pyproject.toml` for rationale).
