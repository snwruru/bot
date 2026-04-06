import asyncio
from math import ceil
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

BOT_TOKEN = "8636727855:AAEIRF7icpCJfQLEllugM9tgnbEaOAPEXp0"


class Form(StatesGroup):
    choosing_object = State()
    waiting_area = State()
    waiting_thickness = State()
    waiting_distance = State()


def object_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Квартира")],
            [KeyboardButton(text="Частный дом")]
        ],
        resize_keyboard=True
    )


def parse_number(text: str) -> Optional[float]:
    text = text.strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def build_pump_kp(area: float, thickness_mm: float, distance_km: Optional[float]) -> str:
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
    distance_cost = 0.0 if distance_km is None else 5000.0 + distance_km * 100.0

    total = cement_cost + cement_delivery + sand_cost + fuel + workers + profit + distance_cost
    price_per_m2 = total / area

    return f"""Коммерческое предложение

Стоимость устройства полусухой стяжки составляет:
{total:.0f} ₽
({price_per_m2:.0f} ₽/м²)

В стоимость работ включено:
- Доставка материала
- нарезка деформационных швов
- затирка поверхности
- монтаж демпферной ленты
- добавление фиброволокна
- укладка плёнки под стяжку
- укрывочная плёнка

В работе используются:
- мытый Багаевский песок
- цемент марки М500

Гарантия на выполненные работы — 5 лет."""


def build_semi_manual_kp(area: float, thickness_mm: float) -> str:
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

    return f"""Коммерческое предложение

Стоимость устройства полусухой стяжки составляет:
{total:.0f} ₽
({price_per_m2:.0f} ₽/м²)

В стоимость работ включено:
- нарезка деформационных швов
- затирка поверхности
- монтаж демпферной ленты
- добавление фиброволокна
- укладка плёнки под стяжку
- укрывочная плёнка

В работе используются:
- мытый Багаевский песок
- цемент марки М500

Гарантия на выполненные работы — 5 лет."""


dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Form.choosing_object)
    await message.answer(
        "Здравствуйте. Какой у вас объект?",
        reply_markup=object_keyboard()
    )


@dp.message(Form.choosing_object)
async def object_handler(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if text not in ["Квартира", "Частный дом"]:
        await message.answer("Пожалуйста, выберите: Квартира или Частный дом.")
        return

    await state.update_data(object_type=text)
    await state.set_state(Form.waiting_area)
    await message.answer("Введите площадь в м²:", reply_markup=ReplyKeyboardRemove())


@dp.message(Form.waiting_area)
async def area_handler(message: Message, state: FSMContext):
    area = parse_number(message.text or "")
    if area is None or area <= 0:
        await message.answer("Введите корректную площадь, например: 85")
        return

    await state.update_data(area=area)
    await state.set_state(Form.waiting_thickness)
    await message.answer("Введите толщину стяжки в мм, например: 70")


@dp.message(Form.waiting_thickness)
async def thickness_handler(message: Message, state: FSMContext):
    thickness = parse_number(message.text or "")
    if thickness is None or thickness <= 0:
        await message.answer("Введите корректную толщину, например: 70")
        return

    data = await state.get_data()
    object_type = data["object_type"]
    area = data["area"]

    if object_type == "Частный дом":
        await state.update_data(thickness=thickness)
        await state.set_state(Form.waiting_distance)
        await message.answer("Введите расстояние от МКАД в км. Если не нужно учитывать, отправьте 0")
        return

    kp_text = build_semi_manual_kp(area=area, thickness_mm=thickness)
    await message.answer(kp_text)
    await state.clear()


@dp.message(Form.waiting_distance)
async def distance_handler(message: Message, state: FSMContext):
    distance = parse_number(message.text or "")
    if distance is None or distance < 0:
        await message.answer("Введите корректное расстояние, например: 25")
        return

    data = await state.get_data()
    area = data["area"]
    thickness = data["thickness"]

    distance_value = None if distance == 0 else distance
    kp_text = build_pump_kp(area=area, thickness_mm=thickness, distance_km=distance_value)

    await message.answer(kp_text)
    await state.clear()


async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())