import os
import pygsheets as pg
from environs import Env
from loguru import logger
from scraper.models import HotelRecord

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class GoogleSheetsManager:
    _HEADERS = [
        'mark', 'id', 'name', 'stars', 'rating', 'number_of_review',
        'district', 'city', 'new_mark', 'date_parsed', 'link', 'foto',
    ]

    def __init__(self):
        self._sheet_id, self._key_path = self._load_config()
        self._client = pg.authorize(service_account_file=self._key_path)
        logger.info("Successfully authorized with Google Sheets.")

    def _load_config(self) -> tuple[str, str]:
        env = Env()
        env.read_env(os.path.join(PROJECT_ROOT, '.env'))
        sheet_id = env('GSHEET_ID')
        key_path = env('KEY_PATH')
        return sheet_id, os.path.join(PROJECT_ROOT, 'config', key_path)

    def update(self, new_records: list[HotelRecord], city: str):
        """Append newly discovered hotels (latest values) to the city worksheet."""
        try:
            spreadsheet = self._client.open_by_key(self._sheet_id)
            sheet, is_new = self._get_or_create_worksheet(spreadsheet, city)
            data_matrix = [r.to_sheets_row() for r in new_records]

            if is_new:
                start_row = 2  # row 1 is headers
            else:
                start_row = self._first_empty_row(sheet)

            sheet.update_values(f"B{start_row}", data_matrix)
            logger.success(f"Successfully appended {len(data_matrix)} new rows to worksheet '{city}'.")
        except Exception as e:
            logger.critical(f"A critical error occurred in update: {e}", exc_info=True)

    def _get_or_create_worksheet(self, spreadsheet, city: str) -> tuple:
        try:
            sheet = spreadsheet.worksheet(property='title', value=city)
            logger.info(f"Worksheet '{city}' found. Preparing to update.")
            return sheet, False
        except Exception:
            logger.warning(f"Worksheet '{city}' not found. Creating a new one.")
            sheet = spreadsheet.add_worksheet(title=city, rows=1000, cols=13)
            sheet.update_row(1, self._HEADERS)
            return sheet, True

    def _first_empty_row(self, sheet) -> int:
        """Return the index of the first empty row (1-based)."""
        all_values = sheet.get_all_values()
        non_empty_count = sum(1 for row in all_values if any(cell for cell in row))
        return max(non_empty_count + 1, 2)
