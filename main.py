# main.py
import asyncio
from bot import bot, dp
from handlers import user_handlers
from db.database import init_db

async def main():
    init_db()  # creates the database on startup
    dp.include_router(user_handlers.router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
