start-welcome = Welcome, { $name }!

btn-trial = 🎁 Try for free
btn-shop = 🛒 Buy VPN
btn-profile = 👤 Profile
btn-support = 🆘 Support

profile-title = 👤 Your Profile
profile-id = ID: { $id }
profile-status = Status: { $status }

subscription-active = ✅ Active until { $date }
subscription-none = ❌ No active subscription

btn-buy = 🛒 Buy Subscription
btn-topup = 💳 Top up Balance
btn-back = 🔙 Back
shop-select-tariff = 📦 Select a tariff:
profile-tariff = 📦 Tariff: { $name }
profile-traffic = 📊 Traffic: { $used } / { $limit } GB ({ $percent }%)
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

support-welcome = 
    👨‍💻 You contacted customer support.
    Describe your problem or ask a question. An operator will reply shortly.
    👋 **Welcome to Support!**
    
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
admin-btn-tariffs = 📦 Tariffs
admin-btn-trial = 🎁 Trial Settings
admin-btn-cp = 💎 Custom Plans
admin-btn-exit = ❌ Exit
admin-exit-msg = 👋 You have exited the admin panel.

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
