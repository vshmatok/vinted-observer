import logging
from html import escape

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)

from src.telegram_bot.routers.start import start_router
from src.telegram_bot.routers.start_searching import start_searching_router
from src.telegram_bot.routers.stop_searching import stop_searching_router
from src.telegram_bot.routers.my_searches import my_searches_router
from src.telegram_bot.routers.new_search import new_search_router
from src.telegram_bot.routers.status import status_router

from src.telegram_bot.utility.keyboard_builder import get_buy_button_keyboard
from src.message_bus.message_bus import MessageBus
from src.message_bus.events.item_found_event import ItemFoundEvent

logger = logging.getLogger(__name__)


class TelegramBot:
    dp: Dispatcher
    bot: Bot
    message_bus: MessageBus

    def __init__(
        self,
        message_bus: MessageBus,
        token: str,
    ):
        self.dp = Dispatcher()
        self.bot = Bot(
            token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.message_bus = message_bus

        self.dp["message_bus"] = message_bus

        self.dp.include_router(start_router)
        self.dp.include_router(start_searching_router)
        self.dp.include_router(stop_searching_router)
        self.dp.include_router(my_searches_router)
        self.dp.include_router(new_search_router)
        self.dp.include_router(status_router)

    async def start(self) -> None:
        """Start bot polling. Raises on critical errors."""
        try:
            logger.info("Starting Telegram bot polling...")
            await self.dp.start_polling(self.bot)
        except TelegramAPIError as e:
            logger.critical(f"Telegram API error during polling: {e}")
            raise
        except Exception as e:
            logger.critical(f"Unexpected error during bot polling: {e}")
            raise

    async def send_new_item_notification(self, event: ItemFoundEvent):
        """Send notification about new item. Logs errors but doesn't raise."""
        try:
            caption_parts = []

            if event.item.title:
                caption_parts.append(f"<b>{escape(event.item.title)}</b>")

            if event.item.total_item_price:
                caption_parts.append(f"💰 <b>{escape(str(event.item.total_item_price))}</b>")

            if event.item.brand_title:
                caption_parts.append(f"🏷️ {escape(event.item.brand_title)}")

            if event.item.size_title:
                caption_parts.append(f"📏 Size: {escape(event.item.size_title)}")

            if event.item.url:
                caption_parts.append(f'\n🔗 <a href="{escape(event.item.url)}">View on Vinted</a>')

            caption = "\n".join(caption_parts)

            buy_keyboard = None
            if event.item.buy_url:
                buy_keyboard = get_buy_button_keyboard(event.item.buy_url)

            photo_url = None
            if event.item.photo and event.item.photo.full_size_url:
                photo_url = event.item.photo.full_size_url

            if photo_url:
                await self.bot.send_photo(
                    chat_id=event.chat_id,
                    photo=photo_url,
                    caption=caption,
                    reply_markup=buy_keyboard,
                )
            else:
                await self.bot.send_message(
                    chat_id=event.chat_id, text=caption, reply_markup=buy_keyboard
                )

            logger.info(f"Sent notification to chat_id={event.chat_id} for item={event.item.id}")

        except TelegramForbiddenError:
            logger.warning(
                f"Bot was blocked by user chat_id={event.chat_id}. "
                "Cannot send notification."
            )
        except TelegramBadRequest as e:
            logger.error(
                f"Bad request sending notification to chat_id={event.chat_id}: {e}. "
                f"Possible invalid photo URL or malformed message."
            )
        except TelegramRetryAfter as e:
            logger.warning(
                f"Rate limited sending to chat_id={event.chat_id}. "
                f"Retry after {e.retry_after} seconds."
            )
        except TelegramAPIError as e:
            logger.error(
                f"Telegram API error sending to chat_id={event.chat_id}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error sending notification to chat_id={event.chat_id}: {e}",
                exc_info=True,
            )
