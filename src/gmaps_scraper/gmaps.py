import re
import time
from pprint import pprint
from tkinter import messagebox
from typing import List
from urllib.parse import unquote

import pycountry
from colorfulPyPrint.py_color import print_error, print_yellow
from selenium.common.exceptions import NoSuchWindowException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium_web_automation_utils.selenium_utils import get_webdriver
from urllib3.exceptions import NewConnectionError, MaxRetryError

from gmaps_scraper.geo_utils import get_country_code, is_state_in_country, get_city_state_country_from_latlon
from gmaps_scraper.tkinter_utils import CustomUserInputBox

PLACE_RE = re.compile(
    r"https://www\.google\.com/maps/place/([^/]+)/@(-?\d+\.\d+),(-?\d+\.\d+)"
)


def wait_for_url_stable(driver,
                        stability_period: float = 1.0,
                        max_wait: float = 5.0,
                        poll: float = 0.2) -> str:
    """
    Poll driver.current_url every `poll` seconds until it hasn’t changed
    for `stability_period` seconds, or until `max_wait` is exceeded.
    Returns the last observed URL.
    """
    start = time.time()
    last = driver.current_url
    stable_since = time.time()

    while True:
        time.sleep(poll)
        now = time.time()
        curr = driver.current_url

        if curr != last:
            last = curr
            stable_since = now
        elif now - stable_since >= stability_period:
            return curr

        if now - start > max_wait:
            return curr


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
        state = parts[-1].strip() if len(parts) >= 2 else ''
    return city, state, country


def get_google_map_details(additional_required: List[str] = None, additional_optional: List[str] = None, debug=False):
    """
    Launches an interactive Google Maps session and collects place details.

    This function opens maps.google.com in a Selenium‐driven Chrome browser,
    watches for the user to navigate to a place URL, and once the URL has
    stabilized, it scrapes:
      - Place name
      - Latitude & longitude
      - Full address
      - City, state, and country (via offline reverse‐geocoding)

    It then pops up a Tkinter dialog asking the user to confirm these fields,
    along with any additional required or optional fields you specify. After
    confirmation, the data is stored (keyed by the latitude/longitude tuple)
    and the user is asked if they’d like to pick another place.

    Parameters:
        additional_required (List[str], optional):
            A list of custom field names to include in the dialog that
            must be filled before proceeding.
        additional_optional (List[str], optional):
            A list of custom field names to include in the dialog that
            may be left blank.
        debug (bool, optional):
            If True, prints debug logs for URL changes and scraped field values.

    Returns:
        Dict[Tuple[str, str], Dict[str, str]]:
            A mapping from (latitude, longitude) tuples to the final
            dictionary of confirmed field values for each place selected.
    """
    additional_required = additional_required or []
    additional_optional = additional_optional or []
    results = {}

    with get_webdriver() as driver:
        driver.get("https://maps.google.com")
        prev_url = re.sub(r',\d+z.*', '', driver.current_url)

        while True:
            try:
                driver.implicitly_wait(1)
                time.sleep(0.2)
                # Exit gracefully if there is no window
                if not driver.current_url:
                    raise NoSuchWindowException

                # debounce until Maps really stops updating the URL
                try:
                    stable = wait_for_url_stable(driver)
                    curr_url = re.sub(r',\d+z.*', '', stable)
                except (NewConnectionError, MaxRetryError) as e:
                    print_error(f"{e}\nBrowser connection lost; returning collected data.")
                    break

                # skip if same as last processed
                if curr_url == prev_url:
                    continue
                prev_url = curr_url  # mark this as the one we’re handling

                if debug:
                    print_yellow(f"url: {curr_url}")

                m = PLACE_RE.match(curr_url)
                if not m:
                    continue

                if debug:
                    print_yellow(" ✓ URL confirmed as valid place.")

                # name + lat,lon
                name = unquote(m.group(1).replace('+', ' '))
                lat, lon = m.group(2).strip(), m.group(3).strip()

                # address
                try:
                    addr_elem = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@data-tooltip='Copy address']")))
                    addr = addr_elem.get_attribute('aria-label').replace('Address: ', '').strip()
                except TimeoutException as e:
                    print_error(f"No address found: {str(e).split('Stacktrace')[0]}")
                    addr = ''

                # plus code + city, state, country
                try:
                    city, state, country = get_city_state_country_from_latlon(lat=float(lat), lon=float(lon))
                    # If city is not in address, then it was likely a bad presumption, force user to enter
                    if city not in addr:
                        city = ""
                except Exception as e:
                    print_error(f"Geo fallback failed: {e}")
                    city = state = country = ""

                # build dialog fields
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

                if debug:
                    print_yellow("Scraped data")
                    for k, v in fields.items():
                        print_yellow(f"{k}: {v}")

                # determine which keys are mandatory
                required_keys = [k for k in fields if k.endswith('*')]
                missing = None

                # show confirmation dialog
                while True:
                    dialog = CustomUserInputBox(None, fields, missing)
                    res = dialog.result
                    if res is None:
                        # Cancel pressed: skip or end
                        return results

                    # check for blank required keys
                    missing = [k for k in required_keys if not res.get(k, '').strip()]
                    if missing:
                        # preserve user entries and re-show with error
                        fields = res
                        continue

                    # success: strip '*' and record
                    clean = {k.rstrip('*'): v for k, v in res.items()}
                    lat_lon_key = (clean['latitude'], clean['longitude'])
                    results[lat_lon_key] = clean

                    # ask if user wants another pick
                    if not messagebox.askyesno(
                            "Keep going?",
                            " ✓ Captured. Search more?\n"
                            "⮕ Yes: continue searching for new location in Google Maps.\n"
                            "⮕ No: exit and get the data for all locations you searched."
                    ):
                        return results

                    break

            except (NoSuchWindowException, TypeError):
                break

    return results


if __name__ == '__main__':
    pprint(
        get_google_map_details(
            additional_required=['Your name'],
            additional_optional=['Age'],
        )
    )
