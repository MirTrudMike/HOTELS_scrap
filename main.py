from config.logging_config import setup_loguru
from scraper.storage import DataStorage
from scraper.scraper import BookingScraper, ScraperConfig
from scraper.parser import CardParser
from scraper.updater import RecordUpdater
from scraper.sheets import GoogleSheetsManager

logger = setup_loguru()


def main():
    storage = DataStorage()
    city = storage.prompt_city_choice()

    update_mode_input = input("Run in UPDATE MODE? (y/n, default n): ").strip().lower()
    update_mode = update_mode_input == 'y'
    mode_label = "UPDATE MODE" if update_mode else "NEW HOTELS MODE"
    logger.info(f"Running in {mode_label} for {city}")

    url = storage.get_booking_url(city)
    config = ScraperConfig(page_load_timeout=40, element_timeout=15, retry_attempts=5, retry_delay=3.0)

    records = storage.read_base(city, 'hotels')

    with BookingScraper(config) as scraper:
        cards = scraper.scrape(url=url, property_type='Hotels')
        if not cards:
            logger.info(f"No cards found for {city}")
            return
        fresh = CardParser().extract(cards)

    all_records, new_records, changed_records = RecordUpdater().process(fresh, records, update_mode)

    storage.save_base(city, 'hotels', all_records)

    if new_records:
        logger.success(f"PROCESSED {len(new_records)} NEW properties")
        GoogleSheetsManager().update(new_records, city)
    else:
        logger.info(f"No new properties found for {city}")

    if update_mode and changed_records:
        logger.success(f"UPDATED {len(changed_records)} existing properties")


if __name__ == '__main__':
    main()
