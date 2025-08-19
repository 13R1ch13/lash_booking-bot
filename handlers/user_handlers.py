from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from keyboards.menu import main_menu
from states.booking import BookingStates
from services.services import services
from db.database import (
    save_appointment,
    get_user_appointments,
    is_time_range_available,
    delete_user_appointment,
)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import datetime

router = Router()

# ---------- Keyboards ----------
def service_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=s)] for s in services.keys()] + [[KeyboardButton(text="⬅️ Back")]],
        resize_keyboard=True
    )

def date_keyboard():
    today = datetime.date.today()
    dates = []
    for i in range(14):
        day = today + datetime.timedelta(days=i)
        if day.weekday() in [0, 1, 3, 4, 5]:  # Mon, Tue, Thu, Fri, Sat
            dates.append([KeyboardButton(text=day.strftime("%Y-%m-%d"))])
    dates.append([KeyboardButton(text="⬅️ Back")])
    return ReplyKeyboardMarkup(keyboard=dates, resize_keyboard=True)

def time_keyboard(date, service_minutes):
    times = []
    for h in range(9, 19):
        for m in (0, 30):
            start = datetime.time(hour=h, minute=m)
            start_minutes = h * 60 + m
            end_minutes = start_minutes + service_minutes

            if end_minutes > 19 * 60:  # the master works until 19:00
                continue

            start_str = start.strftime("%H:%M")
            if is_time_range_available(date, start_str, service_minutes):
                times.append([KeyboardButton(text=start_str)])

    if not times:
        times = [[KeyboardButton(text="No available time")]]
    times.append([KeyboardButton(text="⬅️ Back")])
    return ReplyKeyboardMarkup(keyboard=times, resize_keyboard=True)

# ---------- Start ----------
@router.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Hello! I'm a booking bot. Choose an action:", reply_markup=main_menu())

# ---------- Booking: start ----------
@router.message(F.text == "📝 Book")
async def book(message: Message, state: FSMContext):
    await message.answer("Choose a service:", reply_markup=service_keyboard())
    await state.set_state(BookingStates.choosing_service)

# ---------- Choose service ----------
@router.message(BookingStates.choosing_service)
async def choose_service(message: Message, state: FSMContext):
    if message.text == "⬅️ Back":
        await state.clear()
        await message.answer("Main menu", reply_markup=main_menu())
        return

    if message.text not in services:
        await message.answer("Please choose a service from the list.")
        return

    await state.update_data(service=message.text)
    await message.answer(
        "📅 Choose a date from the list or enter it manually in the format: 2025-09-01",
        reply_markup=date_keyboard()
    )
    await state.set_state(BookingStates.choosing_date)

# ---------- Choose date (including manual input) ----------
@router.message(BookingStates.choosing_date)
async def choose_date(message: Message, state: FSMContext):
    if message.text == "⬅️ Back":
        await message.answer("Choose a service:", reply_markup=service_keyboard())
        await state.set_state(BookingStates.choosing_service)
        return

    try:
        selected_date = datetime.datetime.strptime(message.text, "%Y-%m-%d").date()
    except ValueError:
        await message.answer("❌ Invalid date format. Enter in the format: 2025-09-01")
        return

    if selected_date < datetime.date.today():
        await message.answer("❌ You can't choose a past date.")
        return

    await state.update_data(date=message.text)
    data = await state.get_data()
    duration = services[data['service']]

    await message.answer(
        f"You chose: {message.text}\nNow pick a time:",
        reply_markup=time_keyboard(message.text, duration)
    )
    await state.set_state(BookingStates.choosing_time)

# ---------- Choose time ----------
@router.message(BookingStates.choosing_time)
async def choose_time(message: Message, state: FSMContext):
    if message.text == "⬅️ Back":
        data = await state.get_data()
        await message.answer(
            "📅 Choose a date from the list or enter it manually in the format: 2025-09-01",
            reply_markup=date_keyboard()
        )
        await state.set_state(BookingStates.choosing_date)
        return

    try:
        datetime.datetime.strptime(message.text, "%H:%M")
    except:
        await message.answer("Please choose a time from the list.")
        return

    await state.update_data(time=message.text)
    data = await state.get_data()

    duration = services[data['service']]
    if not is_time_range_available(data["date"], data["time"], duration):
        await message.answer("⛔ This time is already taken. Please choose another.")
        return

    save_appointment(
        user_id=message.from_user.id,
        username=message.from_user.username or "unknown",
        service=data["service"],
        date=data["date"],
        time=data["time"]
    )

    record = f"✅ Appointment confirmed:\nService: {data['service']}\nDate: {data['date']}\nTime: {data['time']}"
    await message.answer(record, reply_markup=main_menu())
    await state.clear()

# ---------- View appointments ----------
@router.message(F.text == "📅 My appointments")
async def show_my_appointments(message: Message):
    records = get_user_appointments(message.from_user.id)
    if not records:
        await message.answer("You don't have any appointments yet.")
        return

    text = "📋 Your appointments:\n\n"
    for service, date, time in records:
        text += f"• {service} — {date} at {time}\n"
    await message.answer(text)

# ---------- Cancel appointment ----------
@router.message(F.text == "❌ Cancel appointment")
async def cancel_booking(message: Message, state: FSMContext):
    records = get_user_appointments(message.from_user.id)
    if not records:
        await message.answer("You have no active appointments.")
        return

    keyboard = [[KeyboardButton(text=f"{service} — {date} at {time}")]
                for service, date, time in records]
    keyboard.append([KeyboardButton(text="⬅️ Back")])

    await message.answer("Choose the appointment you want to cancel:", reply_markup=ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    ))
    await state.set_state(BookingStates.confirming)

# ---------- Cancellation confirmation ----------
@router.message(BookingStates.confirming)
async def confirm_cancel(message: Message, state: FSMContext):
    if message.text == "⬅️ Back":
        await message.answer("Main menu", reply_markup=main_menu())
        await state.clear()
        return

    try:
        parts = message.text.split(" — ")
        service = parts[0]
        date, time = parts[1].split(" at ")
    except:
        await message.answer("Invalid appointment format. Please choose from the list.")
        return

    delete_user_appointment(message.from_user.id, service, date, time)
    await message.answer("❌ Appointment cancelled.", reply_markup=main_menu())
    await state.clear()
