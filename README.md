# Remnawave Telegram Bot

[English](#english) | [Русский](#русский)

---

<a name="english"></a>
## English

A Telegram bot for selling VPN subscriptions tailored for [Remnawave](https://remnawave.org/).

### Features
- 🛒 **Shop**: Users can select tariffs and purchase subscriptions.
- 🎁 **Trial**: Automated issuance of trial keys via Remnawave API.
- 💳 **Payments**: User-friendly payment flow (Modular architecture: Stars, Yookassa, Platega, Tribute).
- 🏷 **Promo Codes**: System for discounts (Fixed amount or Percentage).
- 🌍 **Multi-language**: Support for English and Russian (Auto-detected).
- 👤 **Profile**: View balance and subscription status.

### Admin Commands
> Note: Commands execute only for users listed in `ADMIN_IDS` in `.env`.

- `/add_tariff NAME PRICE DAYS TRAFFIC_GB`
  - Example: `/add_tariff Premium 199 30 0` (0 = Unlimited traffic)
- `/add_trial DAYS TRAFFIC_GB`
  - Example: `/add_trial 3 1` (3 days, 1 GB limit)
- `/add_promo CODE VALUE IS_PERCENT(1/0) MAX_USES`
  - Example: `/add_promo START50 50 1 100` (Code START50, 50% off, 100 uses)
  - Example: `/add_promo MINUS100 100 0 1` (Code MINUS100, 100 RUB off, 1 use)
- `/support_message USER_ID MESSAGE` - Reply to a user's support ticket.

### Installation & Deployment

#### Prerequisites
- A Linux server (VPS) with Docker and Docker Compose installed.
- A domain name (required for Webhook payments like YooKassa).

#### 1. Clone & Configure
```bash
git clone https://github.com/masseselsev/remnabot.git
cd remnabot
cp .env.example .env
nano .env
```
Fill in the required fields in `.env`:
- `BOT_TOKEN`: From @BotFather.
- `REMNAWAVE_URL` & `REMNAWAVE_API_KEY`: From your Remnawave panel.
- `ADMIN_IDS`: Your Telegram ID.
- `WEBHOOK_URL`: Your domain URL (e.g., `https://your-domain.com/webhook`).

#### 2. Run with Docker
```bash
docker compose up -d --build
```
The bot will start on port `127.0.0.1:8000`. You must configure a Reverse Proxy (Nginx, Caddy, etc.) to forward HTTPS requests from your domain to this local port.

#### 3. Updating
To update the bot to the latest version:
```bash
git pull origin main
docker compose down
docker compose up -d --build
```

#### 4. Backups
A script is provided to backup the database: `scripts/backup_db.sh`.
Add it to your crontab to run daily:
```bash
crontab -e
# Add line: 0 3 * * * /path/to/remnabot/scripts/backup_db.sh
```

---

<a name="русский"></a>
## Русский

Телеграм-бот для продажи VPN подписок, разработанный специально для панели [Remnawave](https://remnawave.org/).

### Возможности
- 🛒 **Магазин**: Выбор тарифов и покупка подписок.
- 🎁 **Пробный период**: Автоматическая выдача ключей через Remnawave API.
- 💳 **Платежи**: Модульная система оплаты (Stars, ЮКасса, Platega, Tribute).
- 🏷 **Промокоды**: Скидки (фиксированная сумма или процент).
- 🌍 **Мультиязычность**: Поддержка русского и английского (автоопределение).
- 👤 **Профиль**: Просмотр баланса и статуса подписки.

### Команды Администратора
> Примечание: Команды работают только для пользователей, указанных в `ADMIN_IDS` в файле `.env`.

- `/add_tariff ИМЯ ЦЕНА ДНИ ТРАФИК_ГБ`
  - Пример: `/add_tariff Premium 199 30 0` (0 = Безлимитный трафик)
- `/add_trial ДНИ ТРАФИК_ГБ`
  - Пример: `/add_trial 3 1` (3 дня, лимит 1 ГБ)
- `/add_promo КОД ЗНАЧЕНИЕ ЭТО_ПРОЦЕНТ(1/0) КОЛ_ВО`
  - Пример: `/add_promo START50 50 1 100` (Код START50, скидка 50%, 100 активаций)
  - Пример: `/add_promo MINUS100 100 0 1` (Код MINUS100, скидка 100 RUB, 1 активация)
- `/support_message USER_ID MESSAGE` - Ответить пользователю в техподдержку.

### Установка и Деплой

#### Требования
- Linux сервер (VPS) с установленным Docker и Docker Compose.
- Доменное имя (обязательно для приема платежей, например, через ЮКассу).

#### 1. Клонирование и Настройка
```bash
git clone https://github.com/masseselsev/remnabot.git
cd remnabot
cp .env.example .env
nano .env
```
Заполните обязательные поля в `.env`:
- `BOT_TOKEN`: От @BotFather.
- `REMNAWAVE_URL` и `REMNAWAVE_API_KEY`: Из вашей панели Remnawave.
- `ADMIN_IDS`: Ваш Telegram ID.
- `WEBHOOK_URL`: URL вашего домена (например, `https://your-domain.com/webhook`).

#### 2. Запуск
```bash
docker compose up -d --build
```
Бот запустится на порту `127.0.0.1:8000`. Вы должны настроить Reverse Proxy (Nginx, Caddy и т.д.) для перенаправления HTTPS запросов с вашего домена на этот локальный порт.

#### 3. Обновление
Чтобы обновить бота до последней версии:
```bash
git pull origin main
docker compose down
docker compose up -d --build
```

#### 4. Бэкапы
В папке `scripts/` есть скрипт для бэкапа базы данных: `backup_db.sh`.
Рекомендуем добавить его в crontab для ежедневного запуска:
```bash
crontab -e
# Добавьте строку: 0 3 * * * /path/to/remnabot/scripts/backup_db.sh
```
