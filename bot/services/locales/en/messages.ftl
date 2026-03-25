start-welcome = { $settings_msg }
start-active-sub-title = ℹ️ <b>Active Subscriptions</b>:
start-active-sub-item = 
    { $index }. 👤 <b>{ $username }</b>
    { $expiry }
    { $traffic }
    { $link }
    ──────────────────
btn-shop = 🛒 Buy VPN
btn-profile = 👤 Profile
btn-devices = 📱 My Devices
btn-yes = ✅ Yes
btn-no = ❌ No
btn-trial = 🎁 3-day trial!
btn-support = 🆘 Support

profile-title = 👤 Your Profile
profile-id = 👤 Tg ID: { $id }
profile-status = Status: { $status }

# Shared components
profile-expiry = 📅 Active until { $date }
profile-expiry-caption = Active until
profile-traffic = 📊 Traffic: { $used } / { $limit } GB ({ $percent }%) { $bar }
profile-link = 🔗 Link: <code>{ $link }</code>

profile-additional-accounts = 
    <b>##########################</b>
    📂 <b>Special Accounts:</b>
profile-account-item = 
    👤 <b>{ $username }</b>
    { $expiry }
    { $traffic }
    { $link }

subscription-active = ✅ Active until { $date }
subscription-expired = ❌ Expired on { $date }
subscription-none = ❌ No active subscription

btn-buy = 🛒 Buy Subscription
btn-topup = 💳 Top up Balance
btn-back = 🔙 Back
shop-select-tariff = 📦 Select a plan:
profile-tariff = 📦 Plan: { $name }
trial-activated = ✅ Trial activated!
trial-active = ✅ Your trial is active!
trial-traffic = 📊 Traffic: { $gb } GB
trial-expires = ⏳ Expires: { $date }
trial-link-caption = Your subscription link:
trial-expired = ❌ Your trial period expired at { $date }. Please purchase a subscription.
trial-failed = ❌ Failed to activate trial. Please contact support.
trial-days = { $count } Days
trial-hours = { $count } Hours
trial-less-day = Less than 1 Day
trial-promo-request = 🎟 Please enter a promo code to activate your 3-day free trial:
trial-promo-invalid = ❌ Invalid or used promo code.
trial-promo-cancelled = ❌ Promo code entry cancelled.

account-found-manual = 
    🔍 **Found existing account:**
    
    👤 Name: { $username }
    📦 Plan: { $tariff }
    📅 Expires: { $expire }
    
    You can link it or create a new one.

btn-use-existing = 🔗 Link Found Account
btn-create-new = 🆕 Create New Account
btn-to-menu = 🔙 Menu

devices-title = 📱 **Connected Devices**
devices-empty = No devices found.
devices-item = 
    📱 <b>{ $model }</b> ({ $platform })
    📅 Last seen: { $last_active }
devices-select-account = 🗂 Select an account to manage devices:
btn-delete-device = 🗑 Disconnect
device-deleted = ✅ Device disconnected.
device-delete-fail = ❌ Failed to disconnect device.
device-confirm-delete = Are you sure you want to disconnect <b>{ $model }</b>?

    You are chatting with an administrator.
    Describe your issue, and we will reply shortly.
    
    Send `/start` or the button below to end the chat.
support-sent = ✅ Message sent.
support-reply = 👨‍💻 Support: { $text }
support-exit = 🚪 Support session ended.
btn-cancel = ❌ Cancel
support-recap-title = 📝 **Chat History:**
support-you = 👤 You
support-agent = 👨‍💻 Support
support-media = [Media]
support-help-text = To get technical support, go here: { $link } and write to the channel's private messages.
support-btn-label = 💬 Support / Поддержка
lang-changed-msg = ✅ Language changed to English.\nMenu updated.
trial-failed-msg = ❌ Failed to activate trial. Please contact support.
shop-disabled-msg = 🛒 Temporary unavailable.
error-context-lost = ❌ Account context lost.
error-profile-load = Error loading profile

# Admin Custom Plans (CP)
admin-cp-title = 💎 **Custom Plans**
admin-cp-list-desc = Select a plan or create a new one:
admin-cp-create-btn = ➕ Create Plan
admin-cp-back-btn = 🔙 Back
admin-cp-create-step1 = 1️⃣ Enter Plan **Name**:
admin-cp-create-step2 = 2️⃣ Enter **Squad UUID** (Internal Squad ID):
admin-cp-create-step3 = 3️⃣ Enter **Traffic (GB)** per month (number):
admin-cp-create-step4 = 4️⃣ Enter **Duration (months)** (0 = infinite/2099):
admin-cp-create-step5 = 5️⃣ Enter **Tag** (or 0 to skip):
admin-cp-val-error = ❌ Enter a number.
admin-cp-created = ✅ Plan **{ $name }** created!
admin-cp-not-found = Plan not found
admin-cp-view-title = 💎 **{ $name }**
admin-cp-view-squad = 🆔 Squad: `{ $squad }`
admin-cp-view-traffic = 📊 Traffic: `{ $traffic } GB/mo`
admin-cp-view-duration = ⏳ Duration: `{ $duration }`
admin-cp-view-tag = 🏷 Tag: `{ $tag }`
admin-cp-btn-grant = 🚀 Grant to User
admin-cp-btn-edit = ✏️ Edit
admin-cp-btn-delete = 🗑 Delete
admin-cp-grant-step1 = 
    🚀 Grant Plan **{ $name }**
    
    1️⃣ Enter **Username** (for panel):
admin-cp-grant-step2 = 2️⃣ Enter **Telegram ID** (number, or 0 if none):
admin-cp-grant-step3 = 3️⃣ Enter **Note** (or 0 if none):
admin-cp-grant-confirm = 
    🚀 **Confirm Grant**
    
    Plan: **{ $name }**
    Username: `{ $username }`
    TG ID: `{ $tgid }`
    Note: `{ $desc }`
admin-cp-btn-confirm = ✅ Create
admin-cp-btn-cancel = ❌ Cancel
admin-cp-grant-success = 
    ✅ **User Created!**
    
    👤 Username: `{ $username }`
    🔗 Link: { $link }
    📊 Traffic: { $traffic } GB/mo
    ⏳ Expire: { $expire }
admin-cp-btn-to-menu = 🔙 Menu

bot-unknown-command = 
    ℹ️ Please select a menu item.
    For technical questions, please contact "Support".

# Admin General
admin-title = 🔧 **Admin Panel**
    Select a section:
admin-btn-tariffs = 📦 Plans
admin-btn-trial = 🎁 Trial Settings
admin-btn-cp = 💎 Custom Plans
admin-btn-exit = ❌ Exit
admin-btn-welcome = 📝 Welcome Message
admin-exit-msg = 👋 You have exited the admin panel.

admin-welcome-title = 📝 **Welcome Message Settings**
    Select a language to edit:
admin-welcome-ru = 🇷🇺 Russian
admin-welcome-en = 🇺🇸 English
admin-welcome-ask = Enter welcome text (HTML supported).\nUse `{"{"}$name{"}"}` for username.\nCurrent text:\n\n`{ $current }`
admin-welcome-success = ✅ Message saved!

# Trial Settings
admin-trial-title = 🎁 **Trial Settings**
admin-trial-info = 
    ⏳ Duration: `{ $days }` days
    📊 Traffic: `{ $traffic }` GB
    🆔 Internal Squad UUID: `{ $squad }`
admin-btn-edit-days = ✏️ Set Days
admin-btn-edit-traffic = ✏️ Set Traffic
admin-btn-edit-squad = ✏️ Set Squad UUID
admin-ask-days = Enter new duration (in days):
admin-set-days-success = ✅ Set: { $val } days
admin-set-days-error = ❌ Please enter a number.
admin-ask-traffic = Enter traffic limit (in GB):
admin-set-traffic-success = ✅ Set: { $val } GB
admin-set-traffic-error = ❌ Please enter a number (float allowed).
admin-ask-squad = Enter new Squad UUID:
admin-set-squad-success = ✅ Set Squad UUID: { $val }

# Misc
admin-deleted = ✅ Deleted
admin-wait = ⏳ ...
admin-invalid-id = ❌ Invalid ID
admin-error = ❌ Error: { $error }
admin-month-short = mo

# Admin Standard Tariffs
admin-t-list-title = 📦 **Standard Plans:**
admin-t-create-btn = ➕ Create Plan
admin-t-create-name = Enter plan name:
admin-t-create-cancel = Cancel
admin-t-create-rub = Enter price in RUB (float):
admin-t-create-stars = Enter price in Stars (int):
admin-t-create-usd = Enter price in USD (float):
admin-t-create-days = Enter duration (days):
admin-t-create-traffic = Enter traffic limit in GB (0 for unlimited):
admin-t-ask-squad = Enter Squad UUID (or 0 for default):
admin-t-val-number = Must be a number.
admin-t-val-int = Must be an integer.
admin-t-created = ✅ Plan **{ $name }** created!
admin-t-deleted = 🗑 Plan deleted.
admin-t-archived = 📁 Tariff archived (cannot delete used tariff).
admin-t-list-btn = List
admin-t-view-title = 📦 **{ $name }**
admin-t-view-prices = Prices: { $rub }₽ / { $stars }⭐️ / { $usd }$
admin-t-view-duration = 📅 Duration: { $days } days
admin-t-view-squad = 🛡 Squad: { $squad }
admin-t-view-traffic = 📊 Traffic Limit: { $traffic } GB
admin-t-btn-grant = 🎁 Give to User
admin-t-grant-ask = Enter user's Telegram ID (numeric):
admin-t-grant-success-full = 
    ✅ Plan <b>{ $tariff }</b> granted!
    
    👤 User: { $user_id } { $username }
    📅 Duration: { $days } days
    📊 Traffic: { $traffic } GB
    
    🔗 Subscription Link:
    { $link }
admin-t-grant-error = ❌ [DEBUG] Failed to grant: { $error }
admin-t-grant-user-not-found = ❌ User with ID { $id } not found in bot database. Ask them to /start first.

# Shop
shop-no-tariffs = 😔 No plans available at the moment.
shop-promo-ask = Have a promo code? Enter it below or click Skip.
shop-promo-skip = Skip
shop-promo-invalid = ❌ Invalid promo code. Try again or Skip.
shop-promo-expired = ❌ Promo code expired.
shop-promo-limit = ❌ Promo code limit reached.
shop-promo-applied = ✅ Promo code { $code } applied!
shop-payment-method-desc = Select payment method:
shop-pay-card = 💳 Card ({ $price } RUB)
shop-pay-stars = ⭐️ Telegram Stars ({ $price } Stars)
shop-pay-btn = 💳 Pay
shop-order-created = 
    ✅ Order #{ $id } created.
    Total: { $price } { $currency }
shop-payment-not-configured = ❌ This payment method is not configured yet.
shop-payment-error = ❌ Payment creation error: { $error }
shop-pay-stars-hint = ☝️ Tap the button above to pay with Stars.
shop-success = ✅ Payment successful! Order #{ $id } completed.
shop-error-fulfillment = ⚠️ Payment successful, but delivery failed. Contact support.
shop-error-not-found = ⚠️ Payment successful, but order not found. Contact support.
