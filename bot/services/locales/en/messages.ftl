start-supporter-greeting = 🌟 <b>Thank you for your support!</b> As a premium user, you get access to bonus features and direct links.
{ "" }
start-welcome = { $settings_msg }

start-active-sub-title = ℹ️ <b>Active Subscriptions</b>:
start-active-sub-item = 
    { $index }. 👤 <b>{ $username }</b>
    { $expiry }
    { $traffic }
    { $link }
    ──────────────────
btn-shop = 🛒 Buy VPN
admin-btn-routing = 🛠 Button Management
admin-btn-proxies = 🌐 Proxy Management
admin-btn-exit = 🚪 Exit

admin-proxies-title = 🌐 <b>Telegram Proxy Management</b>
admin-proxies-empty = Proxy list is empty.
admin-proxy-btn-add = ➕ Add Proxy
admin-proxy-add-step1 = Enter proxy name (e.g., "Germany MTProto"):
admin-proxy-add-step2 = Send the proxy link (tg://proxy?... or t.me/proxy?...):
admin-proxy-success = ✅ Proxy added successfully!
admin-proxy-deleted = 🗑 Proxy deleted.

profile-proxies-title = 🌐 <b>Our Telegram Proxies:</b>
btn-yes = ✅ Yes
btn-no = ❌ No
btn-trial = 🎁 3 days free!
btn-support = 🆘 Support (incl. project 🙃)
btn-instruction = 📖 Instruction
btn-disclaimer = ⚖️ About Project
btn-proxies = 🌐 Telegram Proxy
btn-accept-disclaimer = ✅ Accept Terms

profile-title = 👤 Your Profile
profile-supporter-label = 💎 <b>Project Supporter!</b>
profile-id = 👤 Tg ID: { $id }
profile-status = Status: { $status }

# Shared components
profile-expiry = 📅 Active until { $date }
profile-expiry-caption = Active until
profile-traffic = 📊 Traffic: { $used } / { $limit } GB { $bar }
profile-devices = 📱 Devices: { $count } / { $limit }
profile-link = 🔗 Link: { $link }

profile-additional-accounts = 
    <b>##########################</b>
    📂 <b>Special Accounts:</b>
profile-account-item = 
    👤 <b>{ $username }</b>
    { $expiry }
    { $traffic }
    { $devices }
    { $link }

subscription-active = ✅ Active until { $date }
subscription-expired = ❌ Expired on { $date }
subscription-none = ❌ No active subscription

btn-buy = 🛒 Buy Subscription
btn-topup = 💳 Top up Balance
btn-back = 🔙 Back
btn-delete = 🗑 Delete
btn-cancel = ❌ Cancel
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

# Trial for self or friend choice
btn-trial-for-self = 👤 For myself
btn-trial-for-friend = 👥 For a friend
btn-share-contact = 📲 Select a Friend from Contacts
trial-who-for-title = 
    Who are you creating the trial account for?
trial-self-already-exists = 
    ❌ You already have an active account in the system. 
    
    The free trial (3 days) is only available for brand new users. Check the «Profile» section.
trial-friend-self-gifting-denied = ❌ You cannot gift a trial account to yourself. Please provide another friend's contact.
trial-self-level2-denied = 
    ❌ Creating an account for yourself is only available to <b>level-1 users</b>.
    
    If you registered via someone else's promo code or gift, your account is already created. Check the «Profile» section.
trial-friend-not-level1 = 
    ❌ Creating an account <b>for a friend</b> is only available to level-1 users (whose username is set in the system).
    
    Please register yourself first. If you already have — make sure you have a @username set in Telegram.
trial-friend-request-contact = 
    📲 <b>Share your friend's Telegram contact.</b>
    
    Press the button below and select your friend from the contacts list. The contact must be registered on Telegram.
trial-friend-contact-no-id = 
    ❌ Could not get the Telegram ID from this contact.
    
    Make sure your friend is registered on Telegram and try again.
trial-friend-already-exists = ❌ This user already has an account (Level 1 or 2) in the system.
trial-friend-created =
    ✅ Subscription issued for <b>{ $name }</b>!

    Your friend can now open @GeeseCatapultBot, sign in, and follow the <b>Instruction</b> section for setup.

    Subscription link for adding to <b>Happ</b>:
    <code>{ $link }</code>

trial-friend-failed = ❌ Failed to create an account for your friend. Please contact support.

# Routing Settings
profile-routing-separator = ────────────────────
admin-btn-routing = 🔀 Routing Settings
admin-routing-title = 🔀 Routing Configuration Management
admin-routing-desc = <b>Current Description:</b> { $desc }
admin-routing-btns-count = <b>Buttons added:</b> { $count }
admin-routing-btn-edit-desc = 📝 Edit Description
admin-routing-btn-manage = 📑 Manage Buttons
admin-routing-btn-add-button = ➕ Add Button
admin-routing-btn-clear-buttons = 🗑️ Clear All Buttons
admin-btn-back = 🔙 Back

admin-routing-manage-title = 📑 <b>Created buttons list:</b>
admin-routing-item-edit-title = 
    ✏️ <b>Button Management:</b>
    
    🏷️ <b>Title:</b> { $title }
    🔗 <b>URL:</b> { $url }
admin-routing-btn-edit-title = 📝 Change Title
admin-routing-btn-edit-url = 🔗 Change URL
admin-routing-btn-delete = 🗑️ Delete
admin-routing-delete-confirm = Are you sure you want to delete button "{ $title }"?

admin-routing-input-desc = Enter new description text for the routing section:
admin-routing-input-btn-title = Enter localizable title for the new button:
admin-routing-input-btn-url = Enter URL for the button (e.g., happ://routing/...):
admin-routing-success = ✅ Settings updated successfully!

btn-routing-settings = 🔀 Routing Settings

trial-instruction-title = 📖 <b>Setup Instructions</b>

trial-instruction-profile-hint = Click the 👤 <b>Profile</b> button to see your active subscriptions and links.
trial-instruction-hint = Click 📖 <b>Instruction</b> and follow it to connect.

trial-instruction-http-subtitle = 🔸 <b>Option 1 (links like https://catapult...)</b>
trial-instruction-http-steps = Follow the link and follow the instructions on the page.

trial-instruction-happ-subtitle = 🔸 <b>Option 2 (links like happ://...)</b>
trial-instruction-apps = 
    1️⃣ <b>Download Happ app:</b>
    • <a href="https://play.google.com/store/apps/details?id=com.happproxy">Android (Google Play)</a>
    • <a href="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215?platform=iphone">iPhone / iPad</a>
    • <a href="https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk">Android (.apk)</a>
    • <a href="https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe">Windows (PC)</a>
    • <a href="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215?platform=mac">MacOS</a>
    • <a href="https://github.com/Happ-proxy">Other platforms</a>

trial-instruction-steps = 
    2️⃣ <b>Add a subscription to it:</b>
    • Copy your <code>happ://...</code> link.
    • Open <b>Happ</b> app.
    • Tap the <b>"+"</b> button.
    • If the code is valid, your subscription will appear in your profile.
    
    <i>Where to get a promo code? You can use names (username) of existing first-level users (not tg_xxxxxxxxx) if you know them!
    Attention: after your registration using such a promo code, the user whose username was used will receive a notification of your registration.</i>

referral-notification-msg = 
    🔔 <b>You have a new referral!</b>
    
    A new user registered by your recommendation:
    👤 <b>{ $full_name }</b> (@{ $username }, ID: <code>{ $tg_id }</code>)

admin-referral-notification-msg = 
    📢 <b>Registration via recommendation</b>
    
    🆕 User: <b>{ $full_name }</b> (@{ $username }, ID: <code>{ $tg_id }</code>)
    👥 Recommended by: <b>@{ $referrer_username }</b>
    
    ℹ️ <i>{ $delivery_status }</i>

individual-notification-sent = Individual notification sent.
individual-notification-failed = Individual notification NOT sent (user hasn't started bot or blocked it).

disclaimer-not-accepted-msg = 
    ⚠️ <b>Terms of use must be accepted to receive a trial period.</b>
    
    Please go to ⚖️ <b>About Project</b> section and press "Accept Terms".

disclaimer-accepted-msg = ✅ Thank you! Terms of use accepted. You can now activate your trial period.

disclaimer-text = 
    ⚖️ <b>About Project</b>
    
    This project is strictly non-commercial. All proceeds from subscriptions go entirely towards server costs and technical infrastructure maintenance.
    
    The service is provided on an "as is" basis. We are not responsible for any blocking by government regulators and do not guarantee refunds in case of force majeure circumstances that prevent network operation.
    
    To use the VPN, press the "3 days free!" button. If you then want to support the project financially (from 2000 RUB) and receive a bonus of 2TB (2048 Gigabytes) of traffic monthly for a year, go to the support channel ("Support" button) and notify <b>the channel's private messages</b> about your desire. We'll set everything up perfectly! 😊
    
    <i>WARNING: If the server description indicates, for example, CONSUMPTION x10, it means that traffic consumption there is calculated in tenfold volume. 
    That is: if you download 2GB, the system will count them as 20GB, and 100MB will turn into 1GB. This is due to the peculiarities of traffic billing by the hosting provider of the specified server.</i>
    
    Thank you for supporting the development of a free internet!

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

support-welcome = 
    👋 **Welcome to Support!**
    
    You are chatting with an administrator.
    Describe your issue, and we will reply shortly.
    To end the chat, send `/start`.
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
error-profile-load = Error loading profile
trial-failed-msg = ❌ Failed to activate trial. Please contact support.
shop-disabled-msg = 🛒 Temporary unavailable.
error-context-lost = ❌ Account context lost.

lang-selector-title = Select language:
lang-ru = 🇷🇺 Русский
lang-en = 🇺🇸 English
lang-changed-msg = 
    ✅ Language successfully changed to English.
    User menu updated.

admin-btn-search-user = 🔍 Find user by TgID
admin-btn-promos = 🎟 Promo Codes
admin-error-no-tgid = Cannot get user ID from this message.
admin-error-invalid-tgid = Invalid Telegram ID. Enter a number.
admin-error-no-devices = This account has no connected devices.
admin-error-context-lost = Context lost. Search user again.
admin-error-device-not-found = Device not found.
admin-success-device-deleted = Device successfully disconnected.
admin-error-tariff-not-found = Plan not found.
admin-error-invalid-number = Please enter a valid number.

# Admin Tariffs (unified)
admin-ch-tar-select-title = 🔄 **Change Tariff**
    Select a new tariff for the account:
admin-ch-tar-dur-title = ⏳ **Select Duration**
    Tariff: { $tariff }
    Account: { $account }
admin-ch-tar-manual-ask = 🔢 Enter duration in months (integer):
admin-ch-tar-confirm-title = ⚠️ **Confirm Change**
    
    User ID: <code>{ $tg_id }</code>
    Account (UUID): <code>{ $uuid }</code>
    New Tariff: **{ $tariff }**
    New Duration: **{ $duration }**
    
    Are you sure?
admin-ch-tar-success = ✅ Plan successfully changed!
admin-ch-tar-notify-user = 
    🔔 **Your subscription has been updated!**
    
    An administrator has updated your subscription parameters:
    📦 New Plan: **{ $tariff }**
    ⏳ Duration: **{ $duration }**
admin-ch-tar-notify-admin-group = 
    📢 **Tariff Changed (Admin)**
    
    👤 User: <code>{ $tg_id }</code>
    🆔 UUID: <code>{ $uuid }</code>
    📦 Plan: **{ $tariff }**
    ⏳ Duration: **{ $duration }**
    👨‍💻 By: { $admin }

admin-cp-title = 📦 **Plans**
admin-cp-list-desc = List of available plans:
admin-cp-create-btn = ➕ Create Plan
admin-cp-back-btn = 🔙 Back
admin-cp-create-step1 = 1️⃣ Enter Plan **Name**:
admin-cp-create-step2 = 2️⃣ Enter **Squad UUID** (Internal Squad ID):
admin-cp-create-step3 = 3️⃣ Enter **Traffic (GB)** per month (number):
admin-cp-create-step4 = 4️⃣ Enter **Duration (months)** (0 = infinite/2099):
admin-cp-create-step5 = 5️⃣ Enter **Tag** (or 0 to skip):
admin-cp-val-number = ❌ Enter a number.
admin-cp-val-int = ❌ Enter an integer.
admin-cp-created = ✅ Plan **{ $name }** saved successfully!
admin-cp-not-found = Plan not found
admin-cp-view-title = 📦 **{ $name }**
admin-cp-view-squad = 🆔 Squad: `{ $squad }`
admin-cp-view-traffic = 📊 Traffic: `{ $traffic } GB/mo`
admin-cp-view-duration = ⏳ Duration: `{ $duration }`
admin-cp-view-tag = 🏷 Tag: `{ $tag }`
admin-cp-btn-grant = 🚀 Manual Grant (create new account)
admin-cp-btn-edit = ✏️ Edit
admin-cp-btn-delete = 🗑 Delete
admin-cp-grant-step1 = 
    🚀 **Manual Grant: { $name }**
    
    1️⃣ Enter **Username** (panel only):
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
    ✅ **Account Created!**
    
    👤 Username: `{ $username }`
    🔗 Link: { $link }
    📊 Traffic: { $traffic } GB/mo
    ⏳ Expires: { $expire }
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
admin-welcome-ask = 
    Enter welcome text (HTML supported).
    Use <code>{$name}</code> for username.
    
    Current text:
    <code>{ $current }</code>
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

# (Legacy standard tariffs removed)

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
