import re
from pprint import pprint
from urllib.parse import unquote

import pycountry
from selenium import webdriver
from selenium.common.exceptions import NoSuchWindowException, NoSuchElementException

from update_db_table.countries import get_country_code, is_state_in_country
from colorfulPyPrint.py_color import print_error, print_exception
from utils.sanitize import list_from_string
from utils.tkinter_utils.tkinter_utils import CustomUserInputBox


def get_city_state_country_from_plus_code(plus_code):
    """
    Takes a plus code as input and returns the city, state, and country.

    example:
    Plus Code: R5F7+WV Hackettstown, New Jersey
    City: Hackettstown
    State: New Jersey
    Country: United States

    Plus Code: 5Q4H+R4 Guwahati, Assam, India
    City: Guwahati
    State: Assam
    Country: India

    Plus Code: FFQV+42 Nuevo Laredo, Tamaulipas, Mexico
    City: Nuevo Laredo
    State: Tamaulipas
    Country: Mexico

    Plus Code: HP48+JC Wembley, United Kingdom
    City: Wembley
    State:
    Country: United Kingdom

    :param plus_code:
    :return: A tuple with the city, state and country

    """
    # Use regex to remove the first part containing the plus code
    city_and_country = re.sub(r'^\w+\+\w+\s*', '', plus_code)

    # Split the remaining string by commas
    parts = list_from_string(city_and_country)

    # Extract city
    city = parts[0]

    # Check if last part is a country code
    try:
        # First check if the last item is a state from USA
        if is_state_in_country(parts[-1]):
            state = parts[-1]
            country_name = 'United States'
        else:
            country_name = pycountry.countries.lookup(get_country_code(parts[-1])).name
            state = parts[-2] if len(parts) >= 3 else ''
    except LookupError:
        # If country not found, check if last part is a sub
        country_name = ''
        state = parts[-1].strip() if len(parts) == 2 else ''

    return city, state, country_name


def get_google_map_details(zone_blocking_in_km=0):
    # Function to open message box

    map_detail_dict = {}

    # Create Chrome WebDriver instance
    driver = webdriver.Chrome()

    # Open maps.google.com
    driver.get("https://maps.google.com")

    # Get initial URL
    previous_url = re.sub(r',\d+z.*', "", driver.current_url)

    while True:
        try:
            # Wait for a short interval to avoid high CPU usage
            driver.implicitly_wait(1)
            # Exit gracefully if there is no window
            if not driver.current_url:
                raise NoSuchWindowException

            # Get rid of anything after the lat/lon values
            try:
                current_url = re.sub(r',\d+z.*', "", driver.current_url)
            except Exception as e:
                print_exception(e)
                raise NoSuchWindowException

            # Check if current URL has changed
            if previous_url != current_url:

                # place's name should not have ,:/ in them
                pattern = r"https://www.google.com/maps/place/([^/]+)/@(-?\d+\.\d+),(-?\d+\.\d+)"
                match = re.match(pattern, current_url)

                if match:
                    # Replace + with spaces and unquote name to handle accents
                    name = unquote(match.group(1).strip().replace("+", " "))
                    # Names can not have commas, if they do then we captured it prematurely,
                    # correct name will be in the next loop
                    if ',' in name:
                        continue

                    latitude = match.group(2).strip()
                    longitude = match.group(3).strip()

                    # Find address
                    address_element = driver.find_element("xpath", "//button[@data-tooltip='Copy address']")
                    address = address_element.get_attribute("aria-label").replace('Address: ', '').strip()

                    # Get city, state, country from the Plus code
                    try:
                        plus_code_elem = driver.find_element("xpath", "//button[@data-tooltip='Copy plus code']")
                        plus_code = plus_code_elem.get_attribute("aria-label").replace('Plus code: ', '').strip()
                        city, state, country = get_city_state_country_from_plus_code(plus_code)
                    except NoSuchElementException as e:
                        print_error("Unable to find Plus Code: error: ", str(e))
                        city, state, country = '', '', ''

                    map_data = {
                        "name*": name,
                        "latitude*": latitude,
                        "longitude*": longitude,
                        "address": address,
                        "city*": city,
                        "state": state,
                        "country*": country,
                    }
                    if zone_blocking_in_km:
                        map_data["ZONE BLOCKING (in KM)*"] = zone_blocking_in_km

                    # Open message box to the right of the screen
                    while True:
                        dialog = CustomUserInputBox(None, **map_data)
                        res = dialog.result
                        if res is None:  # Do nothing if "Cancel" is pressed
                            break
                        elif res['country*'] and res['city*'] and res['latitude*'] and res['longitude*']:
                            # Add to list to return
                            clean_res = {key.replace('*', ''): value for key, value in res.items()}
                            map_detail_dict[clean_res['name']] = clean_res
                            break
                        else:
                            print("City, country, latitude and longitude can not be blank")

                # Update previous URL
                previous_url = current_url
        except NoSuchWindowException or TypeError:
            return map_detail_dict


if __name__ == '__main__':
    pprint(get_google_map_details())
