from config.logging_config import setup_loguru
from functions.functions import user_city_choice
from functions.new_properties_checker import check_updates

logger = setup_loguru()

def main():
    city = user_city_choice()
    check_updates(city=city, property_type='hotels')

if __name__ == '__main__':
    main()
