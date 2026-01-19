import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "root.settings")
django.setup()

from aiogram.utils import executor
from bot.dispatcher import dp
import bot.handlers

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
