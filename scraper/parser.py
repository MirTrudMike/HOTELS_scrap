from datetime import datetime
from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from scraper.models import HotelData


class CardParser:
    def parse(
        self, cards: list[WebElement], old_data: list[HotelData]
    ) -> tuple[list[HotelData], list[HotelData]]:
        """Extracts hotel data from card elements. Returns (all_data, new_data)."""
        logger.info("STARTED collecting DATA from cards")
        old_ids = {h.id for h in old_data}
        new_data: list[HotelData] = []

        for card in cards:
            link = self._get_link(card)
            if not link:
                continue
            hotel_id = self._get_id(link)
            if not hotel_id or hotel_id in old_ids:
                continue

            rating, number_of_reviews = self._get_rating(card, hotel_id)
            district, city = self._get_location(card)

            hotel = HotelData(
                id=hotel_id,
                name=self._get_name(card),
                stars=self._get_stars(card),
                rating=rating,
                number_of_reviews=number_of_reviews,
                district=district,
                city=city,
                new_mark=self._check_new_marked(card),
                date_parsed=datetime.now().strftime("%d.%m.%Y"),
                link=link,
                foto=self._get_image_link(card),
            )
            old_data.append(hotel)
            new_data.append(hotel)

        return old_data, new_data

    def _get_link(self, card: WebElement) -> str | None:
        try:
            link_element = card.find_element(By.CSS_SELECTOR, '[data-testid="title-link"]')
            return link_element.get_attribute('href').split('?')[0]
        except Exception:
            return None

    def _get_id(self, link: str) -> str | None:
        try:
            return link.split('/')[-1].replace(".html", "")
        except Exception as e:
            logger.error(f"FAILED to get ID: {e} | LINK: {link}")
            return None

    def _get_name(self, card: WebElement) -> str | None:
        try:
            return card.find_element(By.CSS_SELECTOR, '[data-testid="title"]').text
        except Exception:
            return None

    def _get_stars(self, card: WebElement) -> int:
        try:
            elem = card.find_element(By.CSS_SELECTOR, '[aria-label*="out of 5"]')
            return int(elem.get_attribute("aria-label").split()[0])
        except Exception:
            return 0

    def _get_rating(self, card: WebElement, hotel_id: str) -> tuple[float, int]:
        try:
            elem = card.find_element(By.CSS_SELECTOR, '[data-testid="review-score"]')
            rating = float(elem.text.split('\n')[1])
            reviews = int(elem.text.split('\n')[-1].split()[0].replace(',', ''))
            return rating, reviews
        except Exception:
            return 0.0, 0

    def _get_location(self, card: WebElement) -> tuple[str | None, str | None]:
        try:
            text = card.find_element(By.CSS_SELECTOR, '[data-testid="address"]').text
            if ',' in text:
                district, city = text.split(', ', 1)
                return district, city
            return None, text
        except Exception:
            return None, None

    def _check_new_marked(self, card: WebElement) -> bool:
        return "New to Booking.com" in card.text.split('\n')

    def _get_image_link(self, card: WebElement) -> str | None:
        try:
            return card.find_element(By.CSS_SELECTOR, '[data-testid="image"]').get_attribute('src')
        except Exception:
            return None
