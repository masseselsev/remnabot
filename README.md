# Remnawave Telegram Bot

A Telegram bot for selling VPN subscriptions tailored for [Remnawave](https://remnawave.org/).

## Features
- 🛒 **Shop**: Users can select tariffs and purchase subscriptions.
- 🎁 **Trial**: Automated issuance of trial keys via Remnawave API.
- 💳 **Payments**: User-friendly payment flow (Modular architecture: Stars, Yookassa, Platega, Tribute).
- 🏷 **Promo Codes**: System for discounts (Fixed amount or Percentage).
- 🌍 **Multi-language**: Support for English and Russian (Auto-detected).
- 👤 **Profile**: View balance and subscription status.

## Admin Commands
> Note: Commands execute only for users listed in `ADMIN_IDS` in `.env`.

- `/add_tariff NAME PRICE DAYS TRAFFIC_GB`
  - Example: `/add_tariff Premium 199 30 0` (0 = Unlimited traffic)
- `/add_trial DAYS TRAFFIC_GB`
  - Example: `/add_trial 3 1` (3 days, 1 GB limit)
- `/add_promo CODE VALUE IS_PERCENT(1/0) MAX_USES`
  - Example: `/add_promo START50 50 1 100` (Code START50, 50% off, 100 uses)
  - Example: `/add_promo MINUS100 100 0 1` (Code MINUS100, 100 RUB off, 1 use)

## Setup
1. **Configure Environment**:
   ```bash
   cp .env.example .env
   nano .env
   ```
   Fill in `BOT_TOKEN`, `REMNAWAVE_URL`, `REMNAWAVE_API_KEY`, and `ADMIN_IDS`.

2. **Run with Docker**:
   ```bash
   docker compose up -d --build
   ```

## Development
- **Database**: PostgreSQL (Migrations applied automatically on start).
- **Localization**: FTL files in `bot/services/locales/`.
