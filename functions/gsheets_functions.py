import pygsheets as pg
import os
from environs import Env
from loguru import logger
from functions.file_functions import BASE_DIR


def get_sheet_id_and_path():
    env = Env()
    env.read_env(os.path.join(BASE_DIR, '..', '.env'))
    id = env('GSHEET_ID')
    path = env("KEY_PATH")
    full_oath = os.path.join(BASE_DIR, '..', 'config', path)
    return id, full_oath


def update_google_base(new_data: list, city: str):
    try:
        # Prepare data
        gsheet_id, path = get_sheet_id_and_path()
        data_matrix = [list(h.values()) for h in new_data]

        # Authorize and open sheet
        client = pg.authorize(service_account_file=path)
        base = client.open_by_key(gsheet_id)
        logger.info("Successfully authorized with Google Sheets.")

        # Find or create a worksheet
        try:
            sheet = base.worksheet(property='title', value=city)
            logger.info(f"Worksheet '{city}' found. Preparing to update.")
        except pg.WorksheetNotFound:
            logger.warning(f"Worksheet for city '{city}' not found. Creating a new one.")
            sheet = base.add_worksheet(title=city, rows=1000, cols=13)
            # Update headers
            header_row = ['mark', 'id', 'name', 'stars', 'rating', 'number_of_review', 'district',
                          'city', 'new_mark', 'date_parsed', 'link', 'foto']
            sheet.update_row(1, header_row)

        empty_row_index = len(sheet.get_as_df()) + 2
        sheet.update_values(f"B{empty_row_index}", data_matrix)
        logger.info(f"Successfully appended {len(data_matrix)} new rows to worksheet '{city}'.")

    except Exception as e:
        logger.critical(f"A critical error occurred in the update_base function: {e}", exc_info=True)

