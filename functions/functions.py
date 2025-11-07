from functions.file_functions import get_cities



def user_city_choice():
    city_list = list(get_cities())
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
    chosen_city: str = city_list[chosen_num-1]
    print(f"✅ You chose {chosen_city.upper()}")
    return chosen_city
