import re
from pprint import pprint
from typing import List
from urllib.parse import unquote

import pycountry
from colorfulPyPrint.py_color import print_error, print_exception
from selenium.common.exceptions import NoSuchWindowException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_web_automation_utils.selenium_utils import get_webdriver, find_element_wait

from gmaps_scraper.geo_utils import get_country_code, is_state_in_country
from gmaps_scraper.tkinter_utils import CustomUserInputBox


def get_city_state_country_from_plus_code(plus_code: str):
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

    Returns:
        Tuple(city, state, country)
    """
    s = re.sub(r'^\w+\+\w+\s*', '', plus_code)
    parts = [p.strip() for p in s.split(',')]
    city = parts[0]

    # Check if last part is a country code
    try:
        # First check if the last item is a state from USA
        if is_state_in_country(parts[-1]):
            state = parts[-1]
            country = 'United States'
        else:
            country = pycountry.countries.lookup(get_country_code(parts[-1])).name
            state = parts[-2] if len(parts) >= 3 else ''
    except LookupError:
        # If country not found, check if last part is a sub
        country = ''
        state = parts[-1].strip() if len(parts) == 2 else ''
    return city, state, country


def get_google_map_details(additional_required: List[str] = None, additional_optional: List[str] = None):
    additional_required = additional_required or []
    additional_optional = additional_optional or []
    results = {}

    with get_webdriver() as driver:
        driver.get("https://maps.google.com")
        prev_url = re.sub(r',\d+z.*', '', driver.current_url)

        while True:
            try:
                # Wait for a short interval to avoid high CPU usage
                driver.implicitly_wait(1)
                # Exit gracefully if there is no window
                if not driver.current_url:
                    raise NoSuchWindowException

                # Get rid of anything after the lat/lon values
                try:
                    curr_url = re.sub(r',\d+z.*', "", driver.current_url)
                except Exception as e:
                    print_exception(e)
                    raise NoSuchWindowException

                # Check if current URL has changed
                if curr_url != prev_url:
                    m = re.match(r"https://www.google.com/maps/place/([^/]+)/@(-?\d+\.\d+),(-?\d+\.\d+)", curr_url)
                    if m:
                        # Replace + with spaces and unquote name to handle accents
                        name = unquote(m.group(1).replace('+', ' '))
                        # Names can not have commas, if they do then we captured it prematurely,
                        # correct name will be in the next loop
                        if ',' in name:
                            continue

                        # Latitude, Longitude
                        lat, lon = m.group(2).strip(), m.group(3).strip()

                        # Find address
                        addr_elem = find_element_wait(driver, By.XPATH, "//button[@data-tooltip='Copy address']")
                        addr = addr_elem.get_attribute('aria-label').replace('Address: ', '').strip()

                        # Get city, state, country from the Plus code
                        try:
                            plus_elem = find_element_wait(driver, By.XPATH, "//button[@data-tooltip='Copy plus code']")
                            plus = plus_elem.get_attribute('aria-label').replace('Plus code: ', '').strip()
                            city, state, country = get_city_state_country_from_plus_code(plus)
                        except NoSuchElementException as e:
                            print_error(f"No plus code: {e}")
                            city = state = country = ''

                        # build fields dict (with '*' suffix for required)
                        fields = {
                            "name*": name,
                            "latitude*": lat,
                            "longitude*": lon,
                            "address": addr,
                            "city*": city,
                            "state": state,
                            "country*": country,
                        }
                        for f in additional_required:
                            fields[f + '*'] = ''
                        for f in additional_optional:
                            fields[f] = ''

                        # determine which keys are mandatory
                        required_keys = [k for k in fields if k.endswith('*')]
                        missing = None

                        # loop until required fields are filled or user cancels
                        while True:
                            dialog = CustomUserInputBox(None, fields, missing)
                            res = dialog.result
                            if res is None:
                                # User pressed Cancel
                                break

                            # check for any blank required keys
                            missing = [k for k in required_keys if not res.get(k, '').strip()]
                            if missing:
                                # preserve user entries and re-show with error
                                fields = res
                                continue

                            # success: strip '*' and record
                            clean = {k.rstrip('*'): v for k, v in res.items()}
                            results[clean['name']] = clean
                            break

                    # Update previous URL
                    prev_url = curr_url
            except (NoSuchWindowException, TypeError):
                break

    return results


if __name__ == '__main__':
    pprint(get_google_map_details(
        additional_required=['Your name', 'Age'],
        additional_optional=['Last Name'],
    ))
