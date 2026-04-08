import aiomax
from math import ceil
from typing import Optional

BOT_TOKEN = "f9LHodD0cOLxgxYASgo9UR6wYQ2Mrz-sAZU5H3lUi4d_ImxLNUAvbFiqdE1-t25jMnuCZ98nDNGWDVrDmRVi"
if not BOT_TOKEN:
    raise ValueError("Не задан BOT_TOKEN")

bot = aiomax.Bot(BOT_TOKEN)

user_data: dict[int, dict] = {}
ADMIN_ID = 232526477


def parse_number(text: str) -> Optional[float]:
    text = (text or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def is_valid_phone(text: str) -> bool:
    digits = "".join(ch for ch in text if ch.isdigit())
    return len(digits) >= 10


def reset_user(user_id: int) -> None:
    user_data[user_id] = {"step": "choose_object"}


def start_keyboard():
    kb = aiomax.buttons.KeyboardBuilder()
    kb.add(aiomax.buttons.CallbackButton("Квартира", "obj_flat"))
    kb.row(aiomax.buttons.CallbackButton("Частный дом", "obj_house"))
    return kb


def distance_keyboard():
    kb = aiomax.buttons.KeyboardBuilder()
    kb.add(aiomax.buttons.CallbackButton("Без учета расстояния", "distance_none"))
    kb.row(aiomax.buttons.CallbackButton("Начать заново", "restart"))
    return kb


def result_keyboard():
    kb = aiomax.buttons.KeyboardBuilder()
    kb.add(aiomax.buttons.CallbackButton("Оставить заявку", "send_order"))
    kb.row(aiomax.buttons.CallbackButton("Начать заново", "restart"))
    return kb


def calculate_pump(area: float, thickness_mm: float, distance_km: Optional[float]):
    volume = area * thickness_mm / 1000.0

    cement_bags = volume * 5
    cement_cost = cement_bags * 460

    cement_weight_kg = cement_bags * 50
    if cement_weight_kg <= 3000:
        cement_delivery = 5000.0
    elif cement_weight_kg <= 5000:
        cement_delivery = 10000.0
    else:
        cement_delivery = 15000.0

    if volume <= 11:
        sand_cost = 1600 * volume + 6500
    else:
        sand_cost = 1700 * volume + 8500

    workers = max(area * 350, 35000.0)

    if area <= 150.0:
        profit = 25000.0
    elif area <= 200.0:
        profit = 35000.0
    elif area <= 300.0:
        profit = 40000.0
    else:
        profit = 45000.0

    fuel = 5000.0
    distance_cost = 0.0 if distance_km is None else 10000.0 + distance_km * 200.0

    total = cement_cost + cement_delivery + sand_cost + fuel + workers + profit + distance_cost
    price_per_m2 = total / area

    kp = f"""🏗 Коммерческое предложение
━━━━━━━━━━━━━━━━━━━━

💰 Общая стоимость: {total:.0f} ₽
📊 Цена за 1м²: {price_per_m2:.0f} ₽/м²
📐 Площадь: {area} м²
📏 Толщина: {thickness_mm} мм

━━━━━━━━━━━━━━━━━━━━
✅ В стоимость включено:

• Доставка материала
• Нарезка деформационных швов
• Затирка поверхности
• Монтаж демпферной ленты
• Добавление фиброволокна
• Укладка плёнки под стяжку
• Укрывочная плёнка

━━━━━━━━━━━━━━━━━━━━
🔧 Материалы:

• Мытый Багаевский песок
• Цемент марки М500

🛡 Гарантия на выполненные работы — 5 лет"""
    return kp, total


def calculate_semi_manual(area: float, thickness_mm: float):
    volume = area * thickness_mm / 1000.0

    sand_bags = volume * 50
    sand_cost = sand_bags * 60

    cement_bags = volume * 5
    cement_cost = cement_bags * 460

    delivery_trips = ceil(max(sand_bags / 100.0, cement_bags / 10.0))
    delivery_cost = delivery_trips * 5000

    loaders_cost = volume * 1.6 * 1500
    fuel = 2000.0
    workers = 30000.0
    profit = 15000.0

    total = sand_cost + cement_cost + delivery_cost + loaders_cost + fuel + workers + profit
    price_per_m2 = total / area

    kp = f"""🏗 Коммерческое предложение
━━━━━━━━━━━━━━━━━━━━

💰 Общая стоимость: {total:.0f} ₽
📊 Цена за 1м²: {price_per_m2:.0f} ₽/м²
📐 Площадь: {area} м²
📏 Толщина: {thickness_mm} мм

━━━━━━━━━━━━━━━━━━━━
✅ В стоимость включено:

• Нарезка деформационных швов
• Затирка поверхности
• Монтаж демпферной ленты
• Добавление фиброволокна
• Укладка плёнки под стяжку
• Укрывочная плёнка

━━━━━━━━━━━━━━━━━━━━
🔧 Материалы:

• Мытый Багаевский песок
• Цемент марки М500

🛡 Гарантия на выполненные работы — 5 лет"""
    return kp, total


async def send_welcome(target) -> None:
    await target.reply(
        "👋 Здравствуйте!\n\n"
        "Я помогу рассчитать стоимость полусухой стяжки пола.\n\n"
        "🏠 Какой у вас объект?",
        keyboard=start_keyboard()
    )


@bot.on_command("start")
async def start_handler(ctx: aiomax.CommandContext):
    user_id = ctx.message.sender.user_id
    reset_user(user_id)
    await send_welcome(ctx)


@bot.on_bot_start()
async def bot_started(payload: aiomax.BotStartPayload):
    # Безопасно пробуем получить user_id из разных возможных атрибутов
    user_id = None
    for attr in ["user_id", "user", "chat", "sender"]:
        try:
            obj = getattr(payload, attr, None)
            if obj is None:
                continue
            if isinstance(obj, int):
                user_id = obj
            else:
                user_id = getattr(obj, "user_id", None)
            if user_id is not None:
                break
        except Exception:
            continue

    if user_id is not None:
        reset_user(user_id)

    await payload.send(
        "👋 Здравствуйте!\n\n"
        "Я помогу рассчитать стоимость полусухой стяжки пола.\n\n"
        "🏠 Какой у вас объект?",
        keyboard=start_keyboard()
    )


@bot.on_button_callback()
async def callback_handler(callback: aiomax.Callback):
    user_id = callback.user.user_id
    payload = callback.payload

    if user_id not in user_data:
        reset_user(user_id)

    state = user_data[user_id]

    if payload == "restart":
        reset_user(user_id)

        await callback.answer(
            text="Выберите объект:",
            keyboard=[]
        )

        await callback.send(
            text="👋 Здравствуйте!\n\nЯ помогу рассчитать стоимость полусухой стяжки пола.\n\n🏠 Какой у вас объект?",
            keyboard=start_keyboard()
        )
        return

    if payload == "obj_flat":
        state["object_type"] = "flat"
        state["step"] = "wait_area"

        await callback.answer(
            text="Объект: Квартира 🏢",
            keyboard=[]
        )

        await callback.send("📐 Введите площадь помещения в м²:\n\nНапример: 85")
        return

    if payload == "obj_house":
        state["object_type"] = "house"
        state["step"] = "wait_area"

        await callback.answer(
            text="Объект: Частный дом 🏡",
            keyboard=[]
        )

        await callback.send("📐 Введите площадь помещения в м²:\n\nНапример: 85")
        return

    if payload == "distance_none" and state.get("step") == "wait_distance":
        kp, total = calculate_pump(state["area"], state["thickness"], None)
        state["last_kp"] = kp
        state["last_total"] = total

        await callback.answer(
            text="Расстояние от МКАД: не учитывается",
            keyboard=[]
        )

        await callback.send(
            text=kp,
            keyboard=result_keyboard()
        )
        return

    if payload == "send_order":
        if "last_kp" not in state:
            await callback.answer("Нет данных для отправки")
            return

        state["step"] = "wait_phone"

        await callback.answer(
            text="Перед отправкой заявки укажите номер телефона",
            keyboard=[]
        )

        await callback.send(
            "Отлично 👍\n\n📞 Введите ваш номер телефона, чтобы мы могли с вами связаться:\n\nНапример: +7 999 123-45-67"
        )
        return


@bot.on_message()
async def message_handler(message: aiomax.Message):
    text = (message.body.text or "").strip()
    if not text:
        return

    user_id = message.sender.user_id
    if user_id not in user_data:
        reset_user(user_id)

    # Расширенный список триггеров старта — MAX иногда шлёт "start" как обычное сообщение
    if text.lower() in ["/start", "start", "начать заново", "начать", "очистить"]:
        reset_user(user_id)
        await message.reply(
            "👋 Здравствуйте!\n\n"
            "Я помогу рассчитать стоимость полусухой стяжки пола.\n\n"
            "🏠 Какой у вас объект?",
            keyboard=start_keyboard()
        )
        return

    state = user_data[user_id]

    # Если шаг не определён — сбрасываем на начало
    if "step" not in state:
        reset_user(user_id)
        state = user_data[user_id]

    if state["step"] == "choose_object":
        await message.reply(
            "🏠 Пожалуйста, выберите тип объекта кнопкой ниже:",
            keyboard=start_keyboard()
        )
        return

    if state["step"] == "wait_area":
        area = parse_number(text)
        if area is None or area <= 0:
            await message.reply("⚠️ Введите корректную площадь, например: 85")
            return

        state["area"] = area
        state["step"] = "wait_thickness"
        await message.reply("📏 Введите толщину стяжки в мм:\n\nНапример: 70")
        return

    if state["step"] == "wait_thickness":
        thickness = parse_number(text)
        if thickness is None or thickness <= 0:
            await message.reply("⚠️ Введите корректную толщину, например: 70")
            return

        state["thickness"] = thickness

        if state["object_type"] == "house":
            state["step"] = "wait_distance"
            await message.reply(
                "🗺 Введите расстояние от МКАД в км или нажмите кнопку ниже:",
                keyboard=distance_keyboard()
            )
            return

        kp, total = calculate_semi_manual(state["area"], state["thickness"])
        state["last_kp"] = kp
        state["last_total"] = total

        await message.reply(
            kp,
            keyboard=result_keyboard()
        )
        return

    if state["step"] == "wait_distance":
        distance = parse_number(text)
        if distance is None or distance < 0:
            await message.reply("⚠️ Введите корректное расстояние, например: 25")
            return

        distance_value = None if distance == 0 else distance
        kp, total = calculate_pump(state["area"], state["thickness"], distance_value)
        state["last_kp"] = kp
        state["last_total"] = total

        await message.reply(
            kp,
            keyboard=result_keyboard()
        )
        return

    if state["step"] == "wait_phone":
        phone = text.strip()

        if not is_valid_phone(phone):
            await message.reply("⚠️ Введите корректный номер телефона, например: +7 999 123-45-67")
            return

        state["phone"] = phone

        kp_text = state["last_kp"]
        area = state.get("area", 0)
        thickness = state.get("thickness", 0)
        total = state.get("last_total", 0)
        object_type = "Квартира" if state.get("object_type") == "flat" else "Частный дом"

        text_to_admin = f"""🔥 Новая заявка!
━━━━━━━━━━━━━━━━━━━━
👤 Пользователь: {user_id}
📞 Телефон: {phone}
🏠 Объект: {object_type}
📐 Площадь: {area:.0f} м²
📏 Толщина: {thickness:.0f} мм
💰 Стоимость: {total:.0f} ₽
━━━━━━━━━━━━━━━━━━━━

{kp_text}
"""

        await bot.send_message(
            user_id=ADMIN_ID,
            text=text_to_admin
        )

        state["step"] = "done"

        await message.reply("Заявка отправлена! Мы скоро свяжемся с вами 🙌")
        return

    if state["step"] == "done":
        await message.reply(
            "✅ Заявка уже отправлена!\n\nНажмите «Начать заново», если хотите сделать новый расчёт.",
            keyboard=result_keyboard()
        )
        return


if __name__ == "__main__":
    bot.run()
