import os
import json
from loguru import logger


BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # папка, где лежит этот .py файл

def get_cities():
    with open(f"{os.path.join(BASE_DIR, "..", "config", "booking_urls.json")}", mode='r') as file:
        base = json.load(file)
        city_list = dict(base).keys()
    return  city_list


def get_booking_url(city: str) -> str:
    try:
        with open(f"{os.path.join(BASE_DIR, "..", "config", "booking_urls.json")}", mode='r') as file:
            base = json.load(file)
            url = base[city]
        return url
    except Exception as e:
        logger.error(f"❌ ERROR READING booking URL for {city}: {e}")
        return ""

def read_base(city, property_type) -> list:
    try:
        with open(f"{os.path.join(BASE_DIR, '..', 'base', f'{city}_{property_type}.json')}", mode='r') as file:
            base = json.load(file)
        if not base:
            base = []
        return base
    except Exception as e:
        logger.error(f"❌ ERROR READING base File for {city} {property_type}: {e}")
        raise


def update_base(city: str, property_type: str, updated_base: list):
    try:
        with open(f"{os.path.join(BASE_DIR, '..', 'base', f'{city}_{property_type}.json')}", mode='w') as file:
            json.dump(updated_base, file, indent=4, ensure_ascii=False)
            logger.info(f"SUCCESSFULLY updated base file for {city} {property_type}")
        return True
    except Exception as e:
        logger.error(f"❌ ERROR WRITING updated File for {city} {property_type}: {e}")
        return False