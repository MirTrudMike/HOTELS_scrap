import os
import json
from loguru import logger
from scraper.models import HotelRecord

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class DataStorage:
    def __init__(self):
        self._urls_path = os.path.join(PROJECT_ROOT, 'config', 'booking_urls.json')
        self._base_dir = os.path.join(PROJECT_ROOT, 'base')
        self._urls: dict = self._load_urls()

    def _load_urls(self) -> dict:
        with open(self._urls_path, mode='r') as f:
            return json.load(f)

    def get_cities(self) -> list[str]:
        return list(self._urls.keys())

    def get_booking_url(self, city: str) -> str:
        try:
            return self._urls[city]
        except KeyError:
            logger.error(f"❌ No URL found for city: {city}")
            return ""

    def read_base(self, city: str, property_type: str) -> list[HotelRecord]:
        path = os.path.join(self._base_dir, f'{city}_{property_type}.json')
        try:
            with open(path, mode='r') as f:
                raw = json.load(f)
            return [HotelRecord.from_dict(h) for h in raw] if raw else []
        except FileNotFoundError:
            logger.info(f"Base file for {city} {property_type} not found — creating empty base file")
            with open(path, mode='w') as f:
                json.dump([], f)
            return []
        except Exception as e:
            logger.error(f"❌ ERROR READING base file for {city} {property_type}: {e}")
            raise

    def save_base(self, city: str, property_type: str, data: list[HotelRecord]) -> bool:
        path = os.path.join(self._base_dir, f'{city}_{property_type}.json')
        try:
            with open(path, mode='w') as f:
                json.dump([h.to_dict() for h in data], f, indent=4, ensure_ascii=False)
            logger.info(f"SUCCESSFULLY updated base file for {city} {property_type}")
            return True
        except Exception as e:
            logger.error(f"❌ ERROR WRITING base file for {city} {property_type}: {e}")
            return False

    def prompt_city_choice(self) -> str:
        city_list = self.get_cities()
        print("Available cities:\n")
        for num, city in enumerate(city_list, 1):
            print(f"**{num}** {city}")
        print()
        while True:
            chosen_num = int(input("INPUT THE CITY NUMBER\n").strip())
            if chosen_num in range(1, len(city_list) + 1):
                break
            else:
                print("⚠️ WRONG NUMBER ⚠️")
        chosen_city = city_list[chosen_num - 1]
        print(f"✅ You chose {chosen_city.upper()}")
        return chosen_city
