from config.logging_config import setup_loguru
from scraper.storage import DataStorage
from scraper.scraper import BookingScraper, ScraperConfig
from scraper.parser import CardParser
from scraper.sheets import GoogleSheetsManager

logger = setup_loguru()


def main():
    storage = DataStorage()
    city = storage.prompt_city_choice()

    url = storage.get_booking_url(city)
    config = ScraperConfig(page_load_timeout=40, element_timeout=15, retry_attempts=5, retry_delay=3.0)

    old_data = storage.read_base(city, 'hotels')

    with BookingScraper(config) as scraper:
        cards = scraper.scrape(url=url, property_type='Hotels')
        if not cards:
            logger.info(f"No cards found for {city}")
            return
        updated_data, new_data = CardParser().parse(cards, old_data)

    storage.save_base(city, 'hotels', updated_data)
2
    if new_data:
        logger.success(f"PROCESSED {len(new_data)} NEW properties")
        GoogleSheetsManager().update(new_data, city)
    else:
        logger.info(f"No new properties found for {city}")


if __name__ == '__main__':
    main()
