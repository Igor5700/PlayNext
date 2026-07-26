# PlayNext

PlayNext is a Telegram digital goods store with automated product delivery, wallet system, payments, and administration tools.

The project demonstrates a production-oriented Telegram commerce platform with clean architecture, asynchronous backend, database management, and automated order processing.

---

# Features

## Customer

### Product Catalog
- Categories and product search
- Product details
- Digital goods management

### Shopping Flow
- Shopping cart
- Promo codes
- Order creation
- Order history

### Wallet System
- Internal user balance
- Transaction history
- Secure balance operations

### Automatic Delivery
- Automatic digital key delivery after successful payment
- Key inventory management

---

## Admin

### Product Management
- Create and update products
- Category management
- Bulk key upload

### Order Management
- Order monitoring
- Payment tracking
- User management

### Analytics
- Revenue statistics
- Order statistics
- Popular products tracking

---

# Architecture

PlayNext follows Clean Architecture principles with dependencies pointing inward.

```
presentation/
    Telegram Bot (Aiogram)
        |
        ↓

application/
    Use Cases
    Business workflows
    Interfaces
        |
        ↓

domain/
    Entities
    Value Objects
    Business Rules
        |
        ↓

infrastructure/
    Database
    External services
    Implementations
```

## Layers

### Domain

Contains core business logic without framework dependencies:

- Money
- Order
- Cart
- PromoCode
- Business rules and exceptions

---

### Application

Contains application workflows:

- Catalog management
- Checkout process
- Cart operations
- Wallet operations
- Payment processing
- Admin operations

Defines interfaces for:

- repositories
- unit of work
- payment gateways

---

### Infrastructure

Contains external implementations:

- SQLAlchemy repositories
- PostgreSQL database layer
- Alembic migrations
- Crypto Pay integration

---

### Presentation

Telegram interface:

- aiogram routers
- keyboards
- middlewares
- message rendering system

---

# Key Engineering Decisions

- Clean Architecture for separation of business logic and frameworks
- Repository pattern for database abstraction
- Async SQLAlchemy for non-blocking database operations
- Dependency injection through a single composition root
- Atomic wallet operations for safe transactions
- Automated digital delivery after successful payments

---

# Tech Stack

## Backend

- Python 3.12
- Aiogram 3
- SQLAlchemy 2.0 Async
- PostgreSQL
- asyncpg
- Alembic
- Pydantic

## Payments

- Crypto Pay API

## Testing & Quality

- pytest
- Ruff
- mypy strict mode

## Infrastructure

- Docker
- Docker Compose
- Linux VPS

---

# Project Structure

```
src/playnext/

├── core/
│   ├── config
│   ├── logging
│   ├── Money
│   └── exceptions

├── domain/
│   ├── entities
│   ├── enums
│   └── domain errors

├── application/
│   ├── ports
│   │   ├── repositories
│   │   ├── unit of work
│   │   └── payment gateway
│   │
│   └── services
│       ├── catalog
│       ├── cart
│       ├── checkout
│       ├── wallet
│       ├── payment
│       └── admin

├── infrastructure/
│   ├── db
│   ├── repositories
│   └── payments

├── presentation/
│   ├── routers
│   ├── keyboards
│   ├── middlewares
│   └── screen.py

└── bootstrap.py


migrations/
scripts/
tests/
```

---

# Getting Started

## Clone repository

```bash
git clone https://github.com/Inixium/PlayNext.git

cd PlayNext
```

---

## Create environment

Create virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -e ".[dev]"
```

Create environment file:

```bash
cp .env.example .env
```

Configure variables:

```
BOT_TOKEN=
ADMIN_IDS=
DATABASE_URL=
CRYPTO_PAY_TOKEN=
```

Apply migrations:

```bash
alembic upgrade head
```

---

# Running

## Docker

```bash
docker compose up --build
```

Optional demo data:

```bash
docker compose exec bot python scripts/seed.py
```

---

## Local Development

```bash
python scripts/seed.py
```

Run bot:

```bash
python -m playnext
```

---

# Environment Variables

| Variable | Required | Description |
|---|---|---|
| BOT_TOKEN | Yes | Telegram bot token |
| ADMIN_IDS | Yes | Administrator Telegram IDs |
| DATABASE_URL | Yes | PostgreSQL connection string |
| CRYPTO_PAY_TOKEN | No | Crypto Pay API token |
| CRYPTO_PAY_TESTNET | No | Enable test network |
| SENTRY_DSN | No | Error tracking |
| ENVIRONMENT | No | Runtime environment |
| LOG_LEVEL | No | Logging configuration |

---

# Testing

Run tests:

```bash
pytest
```

Code quality:

```bash
ruff check src tests
```

Type checking:

```bash
mypy src
```

---

# Deployment

The project is prepared for production deployment using Docker.

Deployment workflow:

```bash
docker compose up -d --build
```

Includes:

- Docker containerization
- PostgreSQL database
- Automatic migrations
- Persistent storage
- Production environment configuration

---

# Roadmap

Future improvements:

- Advanced catalog filtering
- Product reviews and ratings
- Referral system
- Price monitoring notifications
- Background task queue
- Extended analytics dashboard

---

# License

MIT License