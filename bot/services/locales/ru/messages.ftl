start-welcome = { $settings_msg }
start-active-sub-title = ℹ️ <b>Активные подписки:</b>
start-active-sub-item = 
    { $index }. 👤 <b>{ $username }</b>
    { $expiry }
    { $traffic }
    { $link }
    ──────────────────
btn-shop = 🛒 Купить VPN
btn-profile = 👤 Профиль
btn-devices = 📱 Мои устройства
btn-yes = ✅ Да
btn-no = ❌ Нет
btn-support = 🆘 Поддержка (в т.ч. проекта 🙃)
btn-instruction = 📖 Инструкция
btn-disclaimer = ⚖️ О проекте
btn-accept-disclaimer = ✅ Принять условия
btn-trial = 🎁 3 дня бесплатно!

profile-title = 👤 Ваш профиль
profile-id = 👤 Tg ID: { $id }
profile-status = Статус: { $status }

# Shared components
profile-expiry = 📅 Активна до { $date }
profile-expiry-caption = Активна до
profile-traffic = 📊 Трафик: { $used } / { $limit } GB ({ $percent }%) { $bar }
profile-devices = 📱 Устройств: { $count } / { $limit }
profile-link = 🔗 Ссылка: { $link }

profile-additional-accounts = 
    <b>##########################</b>
    📂 <b>Специальные аккаунты:</b>
profile-account-item = 
    👤 <b>{ $username }</b>
    { $expiry }
    { $traffic }
    { $devices }
    { $link }

subscription-active = ✅ Активна до { $date }
subscription-expired = ❌ Истекла { $date }
subscription-none = ❌ Нет активной подписки

btn-buy = 🛒 Купить подписку
btn-topup = 💳 Пополнить баланс
btn-back = 🔙 Назад
shop-select-tariff = 📦 Выберите тариф:
profile-tariff = 📦 Тариф: { $name }
trial-activated = ✅ Пробный период активирован!
trial-active = ✅ Ваш пробный период активен!
trial-traffic = 📊 Трафик: { $gb } ГБ
trial-expires = ⏳ Истекает: { $date }
trial-link-caption = Ваша ссылка на подписку:
trial-expired = ❌ Ваш пробный период истек { $date }. Пожалуйста, купите подписку.
trial-failed = ❌ Не удалось активировать пробный период. Обратитесь в поддержку.
trial-days = { $count } Дней
trial-hours = { $count } Часов
trial-less-day = Менее 1 дня
trial-promo-request = 🎟 Пожалуйста, введите промокод для активации пробного периода (3 дня):
trial-promo-invalid = ❌ Неверный или использованный промокод.
trial-promo-cancelled = ❌ Ввод промокода отменен.

# Trial for self or friend choice
btn-trial-for-self = 👤 Для себя
btn-trial-for-friend = 👥 Для друга
btn-share-contact = 📲 Выбрать друга из контактов
trial-who-for-title = 
    Для кого вы хотите создать пробный аккаунт?
trial-self-already-exists = 
    ❌ У вас уже есть активный аккаунт в системе. 
    
    Исследование новых возможностей (3 дня бесплатно) доступно только новым пользователям. Проверьте раздел «Профиль».
trial-friend-self-gifting-denied = ❌ Вы не можете подарить триал самому себе. Пожалуйста, укажите контакт одного из ваших друзей.
trial-self-level2-denied = 
    ❌ Создание аккаунта для себя доступно только пользователям <b>первого уровня</b>.
    
    Если вы зарегистрировались через чужой промокод или подарок, ваш аккаунт уже создан. Проверьте раздел «Профиль».
trial-friend-not-level1 = 
    ❌ Создание аккаунта <b>для друга</b> доступно только пользователям первого уровня (чей username задан в системе).
    
    Пожалуйста, сначала зарегистрируйтесь сами. Если вы уже это сделали — убедитесь, что у вас задан @username в Telegram.
trial-friend-request-contact = 
    📲 <b>Поделитесь контактом вашего друга из Telegram.</b>
    
    Нажмите кнопку ниже и выберите друга из списка контактов. Контакт должен быть зарегистрирован в Telegram.
trial-friend-contact-no-id = 
    ❌ Не удалось получить Telegram ID из этого контакта.
    
    Убедитесь, что ваш друг зарегистрирован в Telegram, и попробуйте ещё раз.
trial-friend-already-exists = ❌ У этого пользователя уже есть аккаунт (уровня 1 или 2) в системе.
trial-friend-created =
    ✅ Выдана подписка для <b>{ $name }</b>!

    Теперь ваш друг может перейти в бота @GeeseCatapultBot, авторизоваться, и следовать указаниям из раздела <b>Инструкция</b> для подключения.

    Ссылка на подписку для добавления в <b>Happ</b>:
    <code>{ $link }</code>
trial-friend-failed = ❌ Не удалось создать аккаунт для друга. Пожалуйста, обратитесь в поддержку.


trial-instruction-title = 📖 <b>Инструкция по подключению</b>

trial-instruction-profile-hint = Нажмите кнопку 👤 <b>Профиль</b>, чтобы увидеть ваши активные подписки и ссылки на них.
trial-instruction-hint = Нажмите 📖 <b>Инструкция</b> и следуйте ей для подключения.

trial-instruction-http-subtitle = 🔸 <b>Вариант 1 (ссылки типа https://catapult...)</b>
trial-instruction-http-steps = Перейдите по ссылке и следуйте инструкциям на открывшейся странице.

trial-instruction-happ-subtitle = 🔸 <b>Вариант 2 (ссылки типа happ://...)</b>
trial-instruction-apps = 
    1️⃣ <b>Скачайте приложение Happ:</b>
    • <a href="https://play.google.com/store/apps/details?id=com.happproxy">Android (Google Play)</a>
    • <a href="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215?platform=iphone">iPhone / iPad</a>
    • <a href="https://github.com/Happ-proxy/happ-android/releases/latest/download/Happ.apk">Android (.apk)</a>
    • <a href="https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe">Windows (PC)</a>
    • <a href="https://apps.apple.com/us/app/happ-proxy-utility/id6504287215?platform=mac">MacOS</a>
    • <a href="https://github.com/Happ-proxy">Другие платформы</a>

trial-instruction-steps = 
    2️⃣ <b>Добавьте в него подписку:</b>
    • Скопируйте вашу ссылку <code>happ://...</code>.
    • Откройте приложение <b>Happ</b>.
    • Нажмите на кнопку <b>"+"</b>.
    • Если код верный, ваша подписка сразу появится в профиле.
    
    <i>Где взять промокод? Можно использовать имена (имя пользователя \ username) существующих пользователей первого уровня (не tg_xxxxxxxxx), если вы их знаете!
    Внимание: после вашей регистрации по такому промокоду, пользователю, чей username был использован, придёт оповещение о вашей регистрации.</i>

referral-notification-msg = 
    🔔 <b>У вас новый реферал!</b>
    
    По вашей рекомендации зарегистрировался новый пользователь:
    👤 <b>{ $full_name }</b> (@{ $username }, ID: <code>{ $tg_id }</code>)

admin-referral-notification-msg = 
    📢 <b>Регистрация по рекомендации</b>
    
    🆕 Пользователь: <b>{ $full_name }</b> (@{ $username }, ID: <code>{ $tg_id }</code>)
    👥 Рекомендация от: <b>@{ $referrer_username }</b>
    
    ℹ️ <i>{ $delivery_status }</i>

start-active-sub-title = ℹ️ <b>Активные подписки:</b>

individual-notification-sent = Индивидуальное уведомление отправлено.
individual-notification-failed = Индивидуальное уведомление НЕ отправлено (пользователь не запустил бота или заблокировал его).

disclaimer-not-accepted-msg = 
    ⚠️ <b>Для получения тестового периода необходимо принять условия использования проекта.</b>
    
    Пожалуйста, перейдите в раздел ⚖️ <b>О проекте</b> и нажмите кнопку «Принять условия».

disclaimer-accepted-msg = ✅ Спасибо! Условия использования приняты. Теперь вы можете активировать пробный период.

disclaimer-text = 
    ⚖️ <b>О проекте</b>
    
    Этот проект является абсолютно некоммерческим. Все средства, полученные от подписок, направляются исключительно на оплату серверов и улучшение технической инфраструктуры.
    
    Сервис предоставляется по принципу «как есть» (as is). Мы не несем ответственности за возможные блокировки со стороны государственных регуляторов и не гарантируем возврат средств в случае форс-мажорных обстоятельств, препятствующих работе сети.
    
    Чтобы воспользоваться VPN, нажмите кнопку "3 дня бесплатно!". Если после этого вы захотите поддержать проект финансово (от 2000руб.) и получить за это в качестве бонуса 2ТБ (2048 Гигабайт) трафика ежемесячно в течение года, перейдите в канал поддержки (кнопка "Поддержка") и сообщите <b>в личные сообщения канала</b> о вашем желании. Сделаем всё в лучшем виде! 😊
    
    <i>ВНИМАНИЕ: Если в описании сервера указано, например, РАСХОД х10, значит расход трафика там считается в десятикратном объёме. 
    То есть: если вы скачаете 2Гбайт, система посчитает их как 20Гбайт, а 100Мбайт превратятся в 1Гбайт. Это связано с особенностью тарификации трафика хостинг-провайдером указанного сервера.</i>
    
    Спасибо, что поддерживаете развитие свободного интернета!

account-found-manual = 
    🔍 **Найден существующий аккаунт:**
    
    👤 Имя: { $username }
    📦 Тариф: { $tariff }
    📅 Истекает: { $expire }
    
    Вы можете привязать его или создать новый.

btn-use-existing = 🔗 Привязать этот
btn-create-new = 🆕 Создать новый
btn-to-menu = 🔙 В меню

devices-title = 📱 **Подключенные устройства**
devices-empty = Устройств не найдено.
devices-item = 
    📱 <b>{ $model }</b> ({ $platform })
    📅 Был в сети: { $last_active }
devices-select-account = 🗂 Выберите аккаунт для управления:
btn-delete-device = 🗑 Отключить
device-deleted = ✅ Устройство отключено.
device-delete-fail = ❌ Не удалось отключить устройство.
device-confirm-delete = Вы уверены, что хотите отключить <b>{ $model }</b>?

support-welcome = 
    👋 **Добро пожаловать в службу поддержки!**
    
    Опишите вашу проблему, и администратор ответит вам в ближайшее время.
    Чтобы завершить диалог, отправьте `/start`.

support-sent = ✅ Сообщение отправлено.
support-reply = 👨‍💻 Поддержка: { $text }
support-exit = 🚪 Вы вышли из режима поддержки.
btn-cancel = ❌ Отмена

support-recap-title = 📝 **История переписки:**
support-you = Вы
support-agent = Поддержка
support-media = [Медиа]
support-help-text = Для получения технической поддержки перейдите сюда: { $link } и напишите в личные сообщения канала.
support-btn-label = 💬 Поддержка / Support
trial-failed-msg = ❌ Не удалось активировать пробный период. Обратитесь в поддержку.
shop-disabled-msg = 🛒 Временно недоступно.
error-context-lost = ❌ Контекст аккаунта потерян.
error-profile-load = Ошибка загрузки профиля

lang-selector-title = Выберите язык:
lang-ru = 🇷🇺 Русский
lang-en = 🇺🇸 English
lang-changed-msg = 
    ✅ Язык успешно изменен на русский.
    Меню пользователя обновлено.

admin-btn-search-user = 🔍 Найти пользователя по TgID
admin-btn-promos = 🎟 Промокоды
admin-error-no-tgid = Невозможно получить ID пользователя из этого сообщения.
admin-error-invalid-tgid = Некорректный Telegram ID. Введите число.
admin-error-no-devices = У этого аккаунта нет подключенных устройств.
admin-error-context-lost = Контекст потерян. Повторите поиск пользователя.
admin-error-device-not-found = Устройство не найдено.
admin-success-device-deleted = Устройство успешно отключено.
admin-error-tariff-not-found = Тариф не найден.
admin-error-invalid-number = Пожалуйста, введите корректное число.

# Admin Custom Plans (CP)
admin-cp-title = 💎 **Спецтарифы**
admin-cp-list-desc = Выберите тариф или создайте новый:
admin-cp-create-btn = ➕ Создать Тариф
admin-cp-back-btn = 🔙 Назад
admin-cp-create-step1 = 1️⃣ Введите **Название** тарифа:
admin-cp-create-step2 = 2️⃣ Введите **Squad UUID** (Internal Squad ID):
admin-cp-create-step3 = 3️⃣ Введите **Трафик (GB)** в месяц (число):
admin-cp-create-step4 = 4️⃣ Введите **Срок (мес)** (0 = бессрочно/2099):
admin-cp-create-step5 = 5️⃣ Введите **Тег** (или 0 чтобы пропустить):
admin-cp-val-error = ❌ Введите число.
admin-cp-created = ✅ Тариф **{ $name }** создан!
admin-cp-not-found = Тариф не найден
admin-cp-view-title = 💎 **{ $name }**
admin-cp-view-squad = 🆔 Squad: `{ $squad }`
admin-cp-view-traffic = 📊 Трафик: `{ $traffic } ГБ/мес`
admin-cp-view-duration = ⏳ Длительность: `{ $duration }`
admin-cp-view-tag = 🏷 Тег: `{ $tag }`
admin-cp-btn-grant = 🚀 Выдать пользователю
admin-cp-btn-edit = ✏️ Изменить
admin-cp-btn-delete = 🗑 Удалить
admin-cp-grant-step1 = 
    🚀 Выдача тарифа **{ $name }**
    
    1️⃣ Введите **Username** (для панели):
admin-cp-grant-step2 = 2️⃣ Введите **Telegram ID** (число, или 0 если нет):
admin-cp-grant-step3 = 3️⃣ Введите **Описание/Note** (или 0 если нет):
admin-cp-grant-confirm = 
    🚀 **Подтверждение выдачи**
    
    Тариф: **{ $name }**
    Username: `{ $username }`
    TG ID: `{ $tgid }`
    Note: `{ $desc }`
admin-cp-btn-confirm = ✅ Создать
admin-cp-btn-cancel = ❌ Отмена
admin-cp-grant-success = 
    ✅ **Пользователь создан!**
    
    👤 Username: `{ $username }`
    🔗 Ссылка: { $link }
    📊 Трафик: { $traffic } ГБ/мес
    ⏳ Истекает: { $expire }
admin-cp-btn-to-menu = 🔙 В меню

bot-unknown-command = 
    ℹ️ Выберите пункт меню. 
    По техническим вопросам обращайтесь в раздел "Поддержка".

# Admin General
admin-title = 🔧 **Админ-панель**
    Выберите раздел:
admin-btn-tariffs = 📦 Тарифы
admin-btn-trial = 🎁 Настройки Триала
admin-btn-cp = 💎 Спецтарифы
admin-btn-exit = ❌ Выйти
admin-btn-welcome = 📝 Настройка приветствия
admin-exit-msg = 👋 Вы вышли из админ-панели.

admin-welcome-title = 📝 **Настройка приветствия**
    Выберите язык для редактирования:
admin-welcome-ru = 🇷🇺 Русский
admin-welcome-en = 🇺🇸 English
admin-welcome-ask = 
    Введите текст приветствия (поддерживается HTML).
    Используйте <code>{$name}</code> для имени пользователя.
    
    Текущий текст:
    <code>{ $current }</code>
admin-welcome-success = ✅ Сообщение сохранено!

# Trial Settings
admin-trial-title = 🎁 **Настройки Триала**
admin-trial-info = 
    ⏳ Длительность: `{ $days }` дней
    📊 Трафик: `{ $traffic }` GB
    🆔 Internal Squad UUID: `{ $squad }`
admin-btn-edit-days = ✏️ Задать Дни
admin-btn-edit-traffic = ✏️ Задать Трафик
admin-btn-edit-squad = ✏️ Изменить Squad UUID
admin-ask-days = Введите новую длительность (в днях):
admin-set-days-success = ✅ Установлено: { $val } дней
admin-set-days-error = ❌ Нужно ввести число.
admin-ask-traffic = Введите лимит трафика (в GB):
admin-set-traffic-success = ✅ Установлено: { $val } GB
admin-set-traffic-error = ❌ Нужно ввести число (можно дробное, через точку).
admin-ask-squad = Введите новый Squad UUID:
admin-set-squad-success = ✅ Установлено Squad UUID: { $val }

# Misc
admin-deleted = ✅ Удалено
admin-wait = ⏳ ...
admin-invalid-id = ❌ Некорректный ID
admin-error = ❌ Ошибка: { $error }
admin-month-short = мес

# Admin Standard Tariffs
admin-t-list-title = 📦 **Список тарифов (Standard):**
admin-t-create-btn = ➕ Создать тариф
admin-t-create-name = Введите название тарифа:
admin-t-create-cancel = Отмена
admin-t-create-rub = Цена в рублях (RUB, число):
admin-t-create-stars = Цена в звездах (Stars, целое число):
admin-t-create-usd = Цена в долларах (USD, число):
admin-t-create-days = Длительность (дней):
admin-t-create-traffic = Лимит трафика в ГБ (0 для безлимита):
admin-t-ask-squad = Введите UUID отряда (или 0 для значения по умолчанию):
admin-t-val-number = Нужно ввести число.
admin-t-val-int = Нужно ввести целое число.
admin-t-created = ✅ Тариф **{ $name }** создан!
admin-t-deleted = 🗑 Тариф удален.
admin-t-archived = 📁 Тариф архивирован (нельзя удалить используемый).
admin-t-list-btn = Список
admin-t-view-title = 📦 **{ $name }**
admin-t-view-prices = Цены: { $rub }₽ / { $stars }⭐️ / { $usd }$
admin-t-view-duration = 📅 Срок: { $days } дн.
admin-t-view-squad = 🛡 Отряд: { $squad }
admin-t-view-traffic = 📊 Трафик: { $traffic } ГБ
admin-t-btn-grant = 🎁 Выдать пользователю
admin-t-grant-ask = Введите Telegram ID пользователя (цифры):
admin-t-grant-success-full = 
    ✅ Тариф <b>{ $tariff }</b> выдан!
    
    👤 User: { $user_id } { $username }
    📅 Срок: { $days } дн.
    📊 Трафик: { $traffic } ГБ
    
    🔗 Cсылка на подписку:
    { $link }
admin-t-grant-error = ❌ Ошибка выдачи: { $error }
admin-t-grant-user-not-found = ❌ Пользователь с ID { $id } не найден в базе бота. Попросите его сначала нажать /start.

# Shop
shop-no-tariffs = 😔 Нет доступных тарифов.
shop-promo-ask = Есть промокод? Введите его ниже или нажмите "Пропустить".
shop-promo-skip = Пропустить
shop-promo-invalid = ❌ Неверный промокод. Попробуйте еще раз или пропустите.
shop-promo-expired = ❌ Срок действия промокода истек.
shop-promo-limit = ❌ Лимит использования промокода исчерпан.
shop-promo-applied = ✅ Промокод { $code } применен!
shop-payment-method-desc = Выберите способ оплаты:
shop-pay-card = 💳 Банковская карта ({ $price } RUB)
shop-pay-stars = ⭐️ Telegram Stars ({ $price } Stars)
shop-pay-btn = 💳 Оплатить
shop-order-created = 
    ✅ Заказ #{ $id } создан.
    Сумма к оплате: { $price } { $currency }
shop-payment-not-configured = ❌ Этот способ оплаты еще не настроен.
shop-payment-error = ❌ Ошибка создания платежа: { $error }
shop-pay-stars-hint = ☝️ Нажмите кнопку выше, чтобы оплатить звездами.
shop-success = ✅ Оплата прошла успешно! Ваш заказ #{ $id } выполнен.
shop-error-fulfillment = ⚠️ Оплата прошла, но возникла ошибка при выдаче товара. Свяжитесь с поддержкой.
shop-error-not-found = ⚠️ Оплата прошла, но заказ не найден. Свяжитесь с поддержкой.

