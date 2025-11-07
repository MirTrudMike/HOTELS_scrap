from functions.hotels_scraper import update_properties
from functions.gsheets_functions import update_google_base
from loguru import logger
import asyncio


def check_updates(city: str, property_type: str):
    """Проверяет обновления и отправляет новые объекты администратору"""
    try:
        new_properties =  update_properties(city, property_type)
        if not new_properties:
            logger.info(f"No new properties found for {city} ({property_type})")
            return

        update_google_base(new_properties, city)


    except Exception as e:
        logger.critical(f"Critical error in update check: {str(e)}")
        raise

