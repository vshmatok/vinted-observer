import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.logger import setup_logging
from src.telegram_bot.bot import TelegramBot
from src.search_processor.search_processor import SearchProcessor
from src.message_bus.message_bus import MessageBus
from src.repository.repository import Repository
from src.repository.migrations import MigrationManager
from src.monitoring.monitor import Monitor
from src.monitoring.error_parser import ErrorParser
from src.config import Config
from src.message_bus.events.new_search_event import NewSearchEvent
from src.message_bus.events.remove_search_event import RemoveSearchEvent
from src.message_bus.events.item_found_event import ItemFoundEvent
from src.message_bus.events.start_searching_event import StartSearchingEvent
from src.message_bus.events.stop_searching_event import StopSearchingEvent
from src.message_bus.events.update_search_event import UpdateSearchEvent
from src.message_bus.queries.get_all_searches_query import GetAllSearchesQuery
from src.message_bus.queries.get_search_by_id_query import GetSearchByIdQuery
from src.message_bus.commands.add_new_search_command import AddNewSearchCommand
from src.message_bus.commands.delete_search_command import DeleteSearchCommand
from src.message_bus.commands.update_search_command import UpdateSearchCommand
from src.message_bus.commands.delete_all_listings_for_search_command import (
    DeleteAllListingsForSearchCommand,
)
from src.message_bus.commands.add_listings_for_search_command import (
    AddListingsForSearchCommand,
)
from src.message_bus.queries.filter_new_listings_query import FilterNewListingsQuery
from src.message_bus.queries.get_total_listing_count_for_search_query import (
    GetTotalListingCountForSearchQuery,
)
from src.message_bus.queries.get_recent_found_items_query import (
    GetRecentFoundItemsQuery,
)
from src.message_bus.queries.get_status_report_query import GetStatusReportQuery
from src.vinted_network_client.utils.proxy_manager import ProxyManager

# Setup centralized logging
setup_logging(
    log_level=Config.LOG_LEVEL,
    log_format=Config.LOG_FORMAT,
    log_date_format=Config.LOG_DATE_FORMAT,
    log_file=Config.LOG_FILE,
)
logger = logging.getLogger(__name__)


async def main():
    # Set global startup time
    startup_time = datetime.now()

    # Clear logfile if configured
    if Config.LOG_FILE:
        log_path = Path(Config.LOG_FILE)
        if log_path.exists():
            try:
                open(log_path, "w").close()
                logger.info(f"Cleared existing log file: {Config.LOG_FILE}")
            except Exception as e:
                logger.warning(f"Failed to clear log file {Config.LOG_FILE}: {e}")

    # Validate configuration before starting
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.critical(f"Configuration validation failed: {e}")
        sys.exit(1)

    # Apply database migrations before connecting to repository
    logger.info("Applying database migrations...")
    migration_manager = MigrationManager(Config.DATABASE_PATH)
    if not migration_manager.apply_migrations():
        logger.critical("Failed to apply database migrations. Exiting.")
        sys.exit(1)
    logger.info("Database migrations applied successfully")

    message_bus = MessageBus()
    repository = Repository()

    proxy_list = await Config.load_proxies()
    domain = Config.VINTED_DOMAIN
    proxy_manager: Optional[ProxyManager] = None
    if proxy_list:
        logger.info(f"Loaded {len(proxy_list)} proxies for domain {domain.name}")
        proxy_manager = ProxyManager(proxy_list)
    else:
        logger.info(f"No proxies loaded, proceeding without proxies for {domain.name}")

    try:
        user_agents = await Config.load_user_agents()
        logger.info(f"Loaded {len(user_agents)} user agents")
    except Exception as e:
        logger.critical(f"Failed to load user agents: {e}")
        sys.exit(1)

    pool = SearchProcessor(
        message_bus=message_bus,
        user_agents=user_agents,
        proxy_manager=proxy_manager,
        domain=domain,
    )

    telegram_bot = TelegramBot(message_bus=message_bus, token=Config.TELEGRAM_BOT_TOKEN)
    error_parser = ErrorParser(
        max_count=Config.ERROR_FETCH_AMOUNT,
        path=Config.LOG_FILE,
        log_levels=Config.load_error_log_levels(),
        log_format=Config.LOG_FORMAT,
    )
    monitor = Monitor(
        message_bus=message_bus,
        proxy_manager=proxy_manager,
        startup_time=startup_time,
        error_parser=error_parser,
    )

    # Setup message bus subscriptions
    message_bus.register_event(ItemFoundEvent, telegram_bot.send_new_item_notification)
    message_bus.register_event(NewSearchEvent, pool.add_search)
    message_bus.register_event(RemoveSearchEvent, pool.remove_search)
    message_bus.register_event(StartSearchingEvent, pool.start_searching)
    message_bus.register_event(StopSearchingEvent, pool.stop_searching)
    message_bus.register_event(UpdateSearchEvent, pool.update_search)

    # Setup message bus queries
    message_bus.register_query(GetAllSearchesQuery, repository.get_all_searches)
    message_bus.register_query(GetSearchByIdQuery, repository.get_search_by_id)
    message_bus.register_query(FilterNewListingsQuery, repository.filter_new_listings)
    message_bus.register_query(
        GetTotalListingCountForSearchQuery,
        repository.get_total_listing_count_for_search,
    )
    message_bus.register_query(
        GetRecentFoundItemsQuery, repository.get_recent_found_items
    )
    message_bus.register_query(GetStatusReportQuery, monitor.generate_status_report)

    # Setup message bus commands
    message_bus.register_command(AddNewSearchCommand, repository.add_new_search)
    message_bus.register_command(DeleteSearchCommand, repository.delete_search)
    message_bus.register_command(UpdateSearchCommand, repository.update_search)
    message_bus.register_command(
        AddListingsForSearchCommand, repository.add_listings_to_search
    )
    message_bus.register_command(
        DeleteAllListingsForSearchCommand, repository.delete_all_listings_for_search
    )

    # Repository setup
    try:
        await repository.connect()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.critical(f"Failed to connect to database: {e}")
        sys.exit(1)

    try:
        await repository.cleanup_old_listings()
        logger.info("Old listings cleaned up successfully")
    except Exception as e:
        logger.error(f"Failed to cleanup old listings: {e}")

    # SearchProcessor setup
    try:
        await pool.setup()
        logger.info("Search processor initialized successfully")
    except Exception as e:
        logger.critical(f"Failed to initialize search processor: {e}")
        await repository.close()
        sys.exit(1)

    # Graceful shutdown handling
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    tasks = [
        asyncio.create_task(telegram_bot.start()),
        asyncio.create_task(repository.periodic_cleanup()),
        asyncio.create_task(stop_event.wait()),
    ]

    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        logger.info("Shutting down application...")
        for task in tasks:
            task.cancel()

        try:
            await pool.close()
            logger.info("Search processor closed successfully")
        except Exception as e:
            logger.error(f"Error closing search processor: {e}")

        try:
            await repository.close()
            logger.info("Database connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")


if __name__ == "__main__":
    asyncio.run(main())
