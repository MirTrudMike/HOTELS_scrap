import time
from dataclasses import dataclass
import random
from loguru import logger
from functions.get_data_from_card import get_properties_data
from functions.file_functions import read_base, update_base, get_booking_url
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (WebDriverException,
                                        NoSuchElementException,
                                        TimeoutException,
                                        ElementClickInterceptedException,
                                        StaleElementReferenceException)


@dataclass
class ScraperConfig:
    page_load_timeout: int = 30
    element_timeout: int = 10
    retry_attempts: int = 3
    retry_delay: float = 2.0


def load_page(url: str, config: Optional[ScraperConfig] = None) -> webdriver.Firefox:
    cfg = config or ScraperConfig()

    # Настройка headless-режима
    firefox_options = Options()
    # firefox_options.add_argument("--headless")
    firefox_options.add_argument("--disable-gpu")
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--window-size=1920,1080")

    for attempt in range(cfg.retry_attempts):
        driver = None
        try:
            driver = webdriver.Firefox(options=firefox_options)
            driver.set_page_load_timeout(cfg.page_load_timeout)

            logger.debug(f"Headless browser STARTED")
            driver.get(url)

            # Проверка успешной загрузки
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


def filter_properties(driver: webdriver.Firefox,
                      property_type: str,
                      config: Optional[ScraperConfig] = None) -> int:
    cfg = config or ScraperConfig()
    for attempt in range(cfg.retry_attempts):
        try:
            wait = WebDriverWait(driver, cfg.element_timeout)
            filters = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, '[data-testid="filters-group-label-container"]')
            ))

            target_filter = next((f for f in filters
                                  if f.text.split('\n')[0].strip() == property_type.strip()), None)
            if not target_filter:
                raise NoSuchElementException(f"Filter '{property_type}' not found")

            try:
                max_properties = int(target_filter.text.split('\n')[1])
                target_filter.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].scrollIntoView(); arguments[0].click();", target_filter)

            time.sleep(cfg.retry_delay)
            logger.info(f"Filtered {max_properties} for {property_type}")
            return max_properties

        except Exception as e:
            logger.warning(f"Filter attempt {attempt + 1} failed: {str(e)}")
            if attempt == cfg.retry_attempts - 1:
                raise RuntimeError(f"Failed to apply filter: {str(e)}")
            time.sleep(cfg.retry_delay)


def get_property_cards(driver: webdriver.Firefox,
                       config: Optional[ScraperConfig] = None) -> list[WebElement]:
    cfg = config or ScraperConfig()
    for attempt in range(cfg.retry_attempts):
        try:
            wait = WebDriverWait(driver, cfg.element_timeout)
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


def scroll_to_load_all(driver: webdriver.Firefox, max_properties: int) -> bool:
    logger.info("🚀 Starting page scrolling")
    scroll_attempt = 0
    max_attempts = 300
    max_no_button_scroll = 5
    last_card_count = 0
    consecutive_no_changes = 0

    # Добавляем проверку активности драйвера
    def is_driver_active():
        try:
            driver.current_url  # Простая проверка активности соединения
            return True
        except:
            return False

    try:
        while scroll_attempt < max_attempts and is_driver_active():
            # Проверяем активность перед каждой операцией
            if not is_driver_active():
                logger.critical("💀 Driver connection lost")
                return False

            try:
                current_cards = driver.find_elements(By.CSS_SELECTOR, '[data-testid="property-card-container"]')
            except Exception as e:
                logger.error(f"Element search failed: {str(e)}")
                return False

            current_count = len(current_cards)
            logger.info(f"NOW {current_count} of {max_properties} loaded")

            if current_count >= max_properties:
                logger.success(f"✅ Target reached! Found {current_count}/{max_properties} properties")
                return True

            no_button_count = 0
            while no_button_count < max_no_button_scroll and is_driver_active():
                try:
                    if handle_load_more_button(driver):
                        logger.debug("🔥 Load more button processed")
                        last_card_count = 0
                        break

                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    scroll_attempt += 1
                    no_button_count += 1

                    logger.debug(f"🔄 Scroll #{scroll_attempt} (attempt {no_button_count}/{max_no_button_scroll})")

                    # Увеличиваем задержку при ошибках
                    delay = random.uniform(2.0, 4.0) if scroll_attempt > 10 else 5.0
                    time.sleep(delay)

                    try:
                        new_count = len(driver.find_elements(By.CSS_SELECTOR, '[data-testid="property-card-container"]'))
                    except Exception as e:
                        logger.error(f"Count check failed: {str(e)}")
                        return False

                    if new_count == current_count:
                        consecutive_no_changes += 1
                        if consecutive_no_changes >= 3:  # Уменьшаем лимит
                            logger.warning("⚠️ No changes detected in 3 consecutive scrolls")
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
                    time.sleep(5)  # Увеличиваем задержку при ошибках
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


def handle_load_more_button(driver: webdriver.Firefox) -> bool:
    try:
        button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Load more')]"))
        )
        logger.debug("BUTTON Found")
        button.click()
        # logger.info("Clicked 'Load more' button")
        time.sleep(random.uniform(1.5, 2.5))
        return True
    except Exception as e:
        logger.debug(f"No clickable 'Load more' button: {str(e)}")
        return False


def scrape_properties(url: str,
                      property_type: str,
                      config: Optional[ScraperConfig] = None) -> Optional[webdriver.Firefox]:
    cfg = config or ScraperConfig()
    driver = None

    try:
        driver = load_page(url, cfg)
        # logger.info(f"Started scraping: {url}")

        max_properties = filter_properties(driver, property_type, cfg)

        scroll_to_load_all(driver, max_properties)

        return driver

    except Exception as e:
        logger.critical(f"Scraping failed: {str(e)}")
        if driver:
            driver.quit()
        return None


# Пример использования в другом модуле

def update_properties(city: str, property_type: str) -> list:
    config = ScraperConfig(
        page_load_timeout=40,
        element_timeout=15,
        retry_attempts=5,
        retry_delay=3.0
    )

    url = get_booking_url(city)
    if not url:
        return []
    try:
        driver = scrape_properties(url, property_type.capitalize(), config)
        if not driver:
            return []

        cards = get_property_cards(driver, config)
        logger.info(f"TOTAL cards collected: {len(cards)}")

        old_data = read_base(city, property_type)
        data, new_data = get_properties_data(cards, old_data=old_data)
        logger.info(f"PROCESSED {len(new_data)} NEW properties")

        update_base(city, property_type, data)
        return new_data

    except Exception as e:
        logger.error(f"Update failed: {str(e)}")
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")



