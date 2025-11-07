from selenium.webdriver.common.by import By
from datetime import datetime
from loguru import logger

def get_properties_data(cards: list, old_data=None) -> (list, list):
    logger.info("STARTED collecting DATA from cards")
    if old_data is None:
        old_data = []
    old_ids = list(map(lambda s: s['id'], old_data))
    new_data = []
    for card in cards:
        link = get_link(card)
        if not link:
            continue
        hotel_id = get_id(link)
        if not hotel_id or hotel_id in old_ids:
            continue

        name = get_name(card)
        stars = get_stars(card)
        rating, number_of_reviews = get_rating(card, hotel_id)
        district, city = get_location(card)
        new_mark = check_new_marked(card)
        date_parsed = datetime.now().strftime("%d.%m.%Y")
        image_link = get_image_link(card)

        hotel_data = {
            'id': hotel_id,
            'name': name,
            'stars': stars,
            'rating': rating,
            'number_of_reviews': number_of_reviews,
            'district': district,
            'city': city,
            'new_mark': new_mark,
            'date_parsed': date_parsed,
            'link': link,
            'foto': image_link
        }
        old_data.append(hotel_data)
        new_data.append(hotel_data)
    return old_data, new_data


def get_link(card):
    try:
        link_element = card.find_element(By.CSS_SELECTOR, '[data-testid="title-link"]')
        link = link_element.get_attribute('href').split('?')[0]
        return link
    except:
        return None

def get_id(link: str):
    try:
     hotel_id = link.split('/')[-1].replace(".html", "")
     return hotel_id
    except Exception as e:
        print(f"FAILED to get ID {e} LINK: {link}")
        return None


def get_name(card):
    try:
        name_element = card.find_element(By.CSS_SELECTOR, '[data-testid="title"]')
        name = name_element.text
        return name
    except Exception:
        return None


def get_stars(card):
    try:
        stars_elem = card.find_element(By.CSS_SELECTOR, '[aria-label*="out of 5"]')
        stars = int(stars_elem.get_attribute("aria-label").split()[0])
        return stars

    except Exception:
        return 0

def get_rating(card, un_id):
    try:
        review_elem = card.find_element(By.CSS_SELECTOR, '[data-testid="review-score"]')
        rating = float(review_elem.text.split('\n')[1])
        number_of_reviews = int(review_elem.text.split('\n')[-1].split()[0].replace(',', ''))
        return rating, number_of_reviews

    except Exception as e:
        # logger.error(f"FAILED to collect RATING for ID: {un_id}: {e}")
        return 0, 0

def get_location(card):
    try:
        location_elem = card.find_element(By.CSS_SELECTOR, '[data-testid="address"]')
        location_text = location_elem.text
        if "," in location_text:
            district, city = location_text.split(', ')
        else:
            district, city = None, location_text
        return district, city

    except Exception:
        return None, None


def check_new_marked(card):
    text = card.text.split('\n')
    if "New to Booking.com" in text:
        return True
    return False


def get_image_link(card):
    try:
        image_elem = card.find_element(By.CSS_SELECTOR, '[data-testid="image"]')
        image_link = image_elem.get_attribute('src')
        return image_link
    except Exception:
        return None




