import time
import random
import threading
from dataclasses import dataclass
from typing import Optional
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchElementException,
    ElementClickInterceptedException,
)


@dataclass
class ScraperConfig:
    page_load_timeout: int = 30
    element_timeout: int = 10
    retry_attempts: int = 3
    retry_delay: float = 2.0


class BookingScraper:
    def __init__(
        self,
        config: Optional[ScraperConfig] = None,
        headless: bool = False,
        on_filter_fail: Optional[callable] = None,
        stop_event: Optional[threading.Event] = None,
    ):
        self._config          = config or ScraperConfig()
        self._headless        = headless
        # Callback called when filter cannot be applied.
        # Signature: () -> bool  (True = continue without filter, False = abort)
        self._on_filter_fail  = on_filter_fail
        # Set this event externally to request a graceful stop mid-scrape
        self._stop_event      = stop_event
        self._driver: Optional[webdriver.Firefox] = None

    def _stop_requested(self) -> bool:
        return self._stop_event is not None and self._stop_event.is_set()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self._driver:
            self._driver.quit()
            self._driver = None
            logger.info("Browser closed")

    def scrape(self, url: str, property_type: str) -> list[WebElement]:
        """Loads page, applies filter, scrolls to load all cards, returns card elements."""
        try:
            self._driver = self._load_page(url)
            if self._stop_requested():
                logger.info("Stop requested — aborting after page load")
                return []

            self._dismiss_overlays()
            if self._stop_requested():
                logger.info("Stop requested — aborting after overlay dismissal")
                return []

            max_properties = self._try_filter_properties(property_type)

            if max_properties is None:
                # Filter failed — ask caller what to do via callback
                if self._on_filter_fail and self._on_filter_fail():
                    # User chose to continue; scroll until no new cards appear
                    max_properties = 999_999
                    logger.info("Continuing without filter — will load all visible properties")
                else:
                    logger.info("Scraping aborted by user after filter failure")
                    return []

            if self._stop_requested():
                logger.info("Stop requested — aborting before scroll")
                return []

            self._scroll_to_load_all(max_properties)
            return self._get_property_cards()
        except Exception as e:
            logger.critical(f"Scraping failed: {str(e)}")
            return []

    def _dismiss_overlays(self) -> None:
        """Wait for full page load, then dismiss any blocking banners or overlays."""
        logger.info("Waiting for page to fully load...")
        time.sleep(10)
        try:
            self._driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
            # self._driver.execute_script("document.elementFromPoint(100, 100).click()")
            logger.info("Overlay dismissal complete")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Overlay dismissal (non-critical): {str(e)}")

    def _load_page(self, url: str) -> webdriver.Firefox:
        cfg = self._config
        firefox_options = Options()
        if self._headless:
            firefox_options.add_argument("--headless")
        firefox_options.add_argument("--disable-gpu")
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--window-size=1920,1080")

        for attempt in range(cfg.retry_attempts):
            driver = None
            try:
                driver = webdriver.Firefox(options=firefox_options)
                driver.set_page_load_timeout(cfg.page_load_timeout)
                logger.debug("Headless browser STARTED")
                driver.get(url)

                if "about:blank" in driver.current_url:
                    raise WebDriverException("Page failed to load properly")

                logger.info(f"✅ Successfully loaded page in headless mode: {driver.title}")
                return driver

            except WebDriverException as e:
                logger.warning(f"Attempt {attempt + 1}/{cfg.retry_attempts} failed: {str(e)}")
                if driver:
                    driver.quit()
                if attempt == cfg.retry_attempts - 1:
                    logger.critical("🔥 All loading attempts exhausted")
                    raise
                time.sleep(cfg.retry_delay)

    def _get_filter_checkbox(self, filter_element) -> Optional[WebElement]:
        """Find the checkbox input associated with a filter label container."""
        try:
            return filter_element.find_element(
                By.XPATH, 'ancestor::label/preceding-sibling::input[@type="checkbox"]'
            )
        except Exception:
            return None

    def _is_filter_active(self, filter_element) -> bool:
        """Check if the filter checkbox is currently checked."""
        checkbox = self._get_filter_checkbox(filter_element)
        if checkbox is not None:
            return checkbox.is_selected()
        return False

    def _click_filter(self, filter_element) -> None:
        """Click the label element associated with the filter (the correct interactive target)."""
        try:
            label = filter_element.find_element(By.XPATH, 'ancestor::label')
            label.click()
        except ElementClickInterceptedException:
            checkbox = self._get_filter_checkbox(filter_element)
            if checkbox:
                self._driver.execute_script("arguments[0].click();", checkbox)

    def _try_filter_properties(self, property_type: str) -> Optional[int]:
        """Try to apply the property-type filter. Returns max_properties on success, None on failure."""
        cfg = self._config
        for attempt in range(cfg.retry_attempts):
            try:
                wait = WebDriverWait(self._driver, cfg.element_timeout)
                filters = wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, '[data-testid="filters-group-label-container"]')
                ))

                target_filter = next(
                    (f for f in filters if f.text.split('\n')[0].strip() == property_type.strip()),
                    None
                )
                if not target_filter:
                    raise NoSuchElementException(f"Filter '{property_type}' not found")

                max_properties = int(target_filter.text.split('\n')[1].replace(',', ''))

                if self._is_filter_active(target_filter):
                    logger.info(f"Filter '{property_type}' already active, skipping click")
                else:
                    self._click_filter(target_filter)
                    time.sleep(cfg.retry_delay)
                    logger.info(f"Filter '{property_type}' clicked")

                    # Re-fetch after page reload to verify the filter is now active
                    fresh_filters = self._driver.find_elements(
                        By.CSS_SELECTOR, '[data-testid="filters-group-label-container"]'
                    )
                    fresh_target = next(
                        (f for f in fresh_filters if f.text.split('\n')[0].strip() == property_type.strip()),
                        None
                    )
                    if fresh_target and not self._is_filter_active(fresh_target):
                        logger.warning(f"Filter '{property_type}' toggled off after click, re-enabling")
                        self._click_filter(fresh_target)
                        time.sleep(cfg.retry_delay)

                logger.info(f"Filtered {max_properties} for {property_type}")
                return max_properties

            except Exception as e:
                logger.warning(f"Filter attempt {attempt + 1} failed: {str(e)}")
                if attempt < cfg.retry_attempts - 1:
                    time.sleep(cfg.retry_delay)

        logger.warning(f"All filter attempts exhausted for '{property_type}'")
        return None

    def _get_property_cards(self) -> list[WebElement]:
        cfg = self._config
        for attempt in range(cfg.retry_attempts):
            try:
                wait = WebDriverWait(self._driver, cfg.element_timeout)
                cards = wait.until(EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, '[data-testid="property-card-container"]')
                ))
                logger.debug(f"Found {len(cards)} property cards")
                return cards
            except Exception as e:
                logger.warning(f"Card loading attempt {attempt + 1} failed: {str(e)}")
                if attempt == cfg.retry_attempts - 1:
                    raise RuntimeError(f"Failed to load cards: {str(e)}")
                time.sleep(cfg.retry_delay)

    def _scroll_to_load_all(self, max_properties: int) -> bool:
        logger.info("🚀 Starting page scrolling")
        scroll_attempt = 0
        max_attempts = 300
        max_no_button_scroll = 5
        consecutive_no_changes = 0

        try:
            while scroll_attempt < max_attempts and self._is_driver_active():
                if self._stop_requested():
                    logger.info("Stop requested — halting scroll")
                    return False

                if not self._is_driver_active():
                    logger.critical("💀 Driver connection lost")
                    return False

                try:
                    current_cards = self._driver.find_elements(
                        By.CSS_SELECTOR, '[data-testid="property-card-container"]'
                    )
                except Exception as e:
                    logger.error(f"Element search failed: {str(e)}")
                    return False

                current_count = len(current_cards)
                logger.info(f"NOW {current_count} of {max_properties} loaded")

                if current_count >= max_properties:
                    logger.success(f"✅ Target reached! Found {current_count}/{max_properties} properties")
                    return True

                no_button_count = 0
                while no_button_count < max_no_button_scroll and self._is_driver_active():
                    if self._stop_requested():
                        logger.info("Stop requested — halting scroll")
                        return False

                    try:
                        if self._handle_load_more_button():
                            logger.debug("🔥 Load more button processed")
                            break

                        self._driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        scroll_attempt += 1
                        no_button_count += 1

                        logger.debug(
                            f"🔄 Scroll #{scroll_attempt} (attempt {no_button_count}/{max_no_button_scroll})"
                        )

                        delay = random.uniform(2.0, 4.0) if scroll_attempt > 10 else 5.0
                        time.sleep(delay)

                        try:
                            new_count = len(self._driver.find_elements(
                                By.CSS_SELECTOR, '[data-testid="property-card-container"]'
                            ))
                        except Exception as e:
                            logger.error(f"Count check failed: {str(e)}")
                            return False

                        if new_count == current_count:
                            consecutive_no_changes += 1
                            if consecutive_no_changes >= 3:
                                logger.info("⚠️ No changes detected in 3 consecutive scrolls")
                                return False
                        else:
                            consecutive_no_changes = 0
                            current_count = new_count

                    except Exception as e:
                        logger.error(f"🚨 Scroll error: {str(e)}")
                        if "without establishing a connection" in str(e):
                            logger.critical("💥 Connection lost, aborting")
                            return False
                        if no_button_count >= max_no_button_scroll // 2:
                            return False
                        time.sleep(5)
                        continue

                if no_button_count >= max_no_button_scroll:
                    logger.warning(f"⛔ Reached {max_no_button_scroll} scrolls without button")
                    return False

            logger.error(f"🔴 Max attempts reached ({max_attempts})")
            return False

        except Exception as main_error:
            logger.critical(f"💀 Critical error: {str(main_error)}")
            return False
        finally:
            logger.info("🏁 Ending scroll process")

    def _handle_load_more_button(self) -> bool:
        try:
            button = WebDriverWait(self._driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Load more')]"))
            )
            logger.debug("BUTTON Found")
            button.click()
            time.sleep(random.uniform(1.5, 2.5))
            return True
        except Exception as e:
            logger.debug(f"No clickable 'Load more' button: {str(e)}")
            return False

    def _is_driver_active(self) -> bool:
        try:
            self._driver.current_url
            return True
        except Exception:
            return False
