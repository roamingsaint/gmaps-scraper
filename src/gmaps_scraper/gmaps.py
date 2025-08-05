import re
import time
from pprint import pprint
import tkinter as tk
from tkinter import messagebox
from typing import List, Literal, Dict, Tuple, Union
from urllib.parse import unquote

import pycountry
from colorfulPyPrint.py_color import print_error, print_yellow
from selenium.common.exceptions import NoSuchWindowException, TimeoutException, NoSuchElementException
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium_web_automation_utils.selenium_utils import get_webdriver, find_element_wait
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
    Poll driver.current_url every `poll` seconds until it hasn't changed
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


def get_rating_reviews_category(driver, gmaps_name):
    # 1) jump to the ratings container
    container = driver.find_element(
        By.XPATH,
        f"""//div[h1[text()="{gmaps_name}"]]/following-sibling::div[1]"""
    )

    # 2) rating
    try:
        rating_elem = container.find_element(
            By.XPATH,
            ".//span[contains(@aria-label,'stars')]"
        )
        # pull just the number, e.g. "4.4"
        rating = rating_elem.get_attribute("aria-label").split()[0]
    except NoSuchElementException:
        rating = ""

    # 3) reviews
    try:
        reviews_elem = container.find_element(
            By.XPATH,
            ".//span[contains(@aria-label,'reviews')]"
        )
        # strip commas and “reviews”
        reviews = reviews_elem.get_attribute("aria-label").split()[0].replace(",", "")
    except NoSuchElementException:
        reviews = ""

    # 4) category
    try:
        cat_elem = container.find_element(
            By.XPATH,
            ".//button[contains(@jsaction,'category')]"
        )
        category = cat_elem.text.strip()
    except NoSuchElementException:
        category = ""

    return rating, reviews, category


def get_google_map_details(
    additional_required: List[str] = None,
    additional_optional: List[str] = None,
    search_terms: Union[List[str], str] = None,
    confirmation_mode: Literal["always", "on_missing", "on_required_missing"] = "always",
    debug: bool = False
) -> Dict[Tuple[str, str], Dict[str, str]]:
    """
    Launches a Google Maps session and collects place details, in either batch or fully interactive mode.

    This function opens maps.google.com in a Selenium‐driven Chrome browser,
    waits for the URL to stabilize on a place, and scrapes:
      - Place name
      - Latitude & longitude
      - Full address
      - City, state, country (reverse‐geocode)
      - Rating, Reviews, Category

    It either runs a batch of searches (if `search_terms` is provided) or
    enters manual‐pick mode.  In batch mode it scrapes exactly each term and
    returns immediately.  In manual mode it pops up a Tkinter confirmation dialog
    after each scrape and then repeatedly asks “Keep going?” until you click No.

    Parameters:
        additional_required (List[str], optional):
            Custom field names that **must** be filled in the dialog.
        additional_optional (List[str], optional):
            Custom field names that **may** be left blank.
        search_terms (List[str] or str, optional):
            A term or list of terms to automatically search and scrape.  If omitted,
            you must navigate manually in the map.
        confirmation_mode (Literal["always", "on_missing", "on_required_missing"], optional):
            Controls whether and when to show the confirmation dialog:
              - "always": prompt every time (default in manual mode)
              - "on_missing": prompt only if *any* field is blank
              - "on_required_missing": prompt only if a *required* field is blank
        debug (bool, optional):
            If True, prints debug logs for URL changes and scraped values.

    Returns:
        Dict[Tuple[str, str], Dict[str, str]]:
            Mapping from (latitude, longitude) tuples to your confirmed data.
    """
    additional_required = additional_required or []
    additional_optional = additional_optional or []
    results = {}

    # make a copy, so we don’t mutate the caller’s list
    terms = [search_terms] if isinstance(search_terms, str) else list(search_terms or [])

    with get_webdriver() as driver:
        driver.get("https://maps.google.com")
        # prepare hidden Tk root for messagebox
        _tk_root = tk.Tk()
        _tk_root.withdraw()
        prev_url = re.sub(r',\d+z.*', '', driver.current_url)

        def pick_and_scrape(search_term: str = None):
            nonlocal prev_url, results
            # 1) if a search term is provided, run it
            if search_term:
                search_elem = find_element_wait(driver, By.XPATH, "//form/input")
                search_elem.clear()
                search_elem.send_keys(search_term, Keys.ENTER)

            # 2) wait for the URL to stabilize, then scrape one place
            while True:
                driver.implicitly_wait(1)
                time.sleep(0.2)
                if not driver.current_url:
                    raise NoSuchWindowException()

                try:
                    stable = wait_for_url_stable(driver)
                except (NewConnectionError, MaxRetryError) as e:
                    print_error(f"{e}\nBrowser connection lost; returning collected data.")
                    return

                curr_url = re.sub(r',\d+z.*', '', stable)
                if curr_url == prev_url:
                    continue
                prev_url = curr_url

                if debug:
                    print_yellow(f"url: {curr_url}")

                m = PLACE_RE.match(curr_url)
                if not m:
                    continue

                if debug:
                    print_yellow(" ✓ URL confirmed as valid place.")

                # --- scrape ---
                # name + lat/lon
                name = unquote(m.group(1).replace('+', ' '))
                lat, lon = m.group(2).strip(), m.group(3).strip()

                # address
                try:
                    addr_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@data-tooltip='Copy address']"))
                    )
                    addr = addr_btn.get_attribute('aria-label').replace('Address: ', '').strip()
                except TimeoutException:
                    print_error("No address found")
                    addr = ""

                # city/state/country via reverse‐geocode
                try:
                    city, state, country = get_city_state_country_from_latlon(
                        lat=float(lat), lon=float(lon)
                    )
                    if city not in addr:
                        city = ""
                except Exception as e:
                    print_error(f"Geo fallback failed: {e}")
                    city = state = country = ""

                # rating & reviews
                rating, reviews, category = get_rating_reviews_category(driver, gmaps_name=name)

                # build dialog fields
                fields = {
                    "name*": name,
                    "latitude*": lat,
                    "longitude*": lon,
                    "address": addr,
                    "city*": city,
                    "state": state,
                    "country*": country,
                    "rating": rating,
                    "reviews": reviews,
                    "category": category,
                }
                for f in additional_required:
                    fields[f + '*'] = ''
                for f in additional_optional:
                    fields[f] = ''

                if debug:
                    print_yellow("Scraped data")
                    for k, v in fields.items():
                        print_yellow(f"{k}: {v}")

                # decide if we need confirmation
                required_keys = [k for k in fields if k.endswith('*')]

                if confirmation_mode == "always":
                    needs_confirmation = True
                elif confirmation_mode == "on_missing":
                    needs_confirmation = any(not v.strip() for v in fields.values())
                elif confirmation_mode == "on_required_missing":
                    needs_confirmation = any(not fields[k].strip() for k in required_keys)
                else:
                    raise ValueError(f"Invalid confirmation_mode: {confirmation_mode!r}")

                # if no confirmation needed, save and return immediately
                if not needs_confirmation:
                    clean = {k.rstrip('*'): v for k, v in fields.items()}
                    results[(clean['latitude'], clean['longitude'])] = clean
                    return

                # otherwise fall back to the existing confirmation loop
                missing = None
                while True:
                    dialog = CustomUserInputBox(None, fields, missing)
                    res = dialog.result
                    if res is None:
                        return  # user cancelled

                    # re-check for blank required keys
                    missing = [k for k in required_keys if not res.get(k, '').strip()]
                    if missing:
                        # preserve user entries and re-show with error
                        fields = res
                        continue

                    # strip '*' and save
                    clean = {k.rstrip('*'): v for k, v in res.items()}
                    results[(clean['latitude'], clean['longitude'])] = clean
                    break

                # done scraping one place
                return

        # batch vs manual mode
        if terms:
            # batch mode: run provided searches and return immediately,
            # but always destroy the hidden Tk root even on error
            try:
                for term in terms:
                    pick_and_scrape(term)
                return results
            finally:
                _tk_root.destroy()

        # manual mode: pick once, then ask “Keep going?” until user says no
        pick_and_scrape(None)
        while messagebox.askyesno(
            "Keep going?",
            " ✓ Captured. Search more?\n"
            "⮕ Yes: enter new location in Google Maps.\n"
            "⮕ No: finish and return all results."
        ):
            pick_and_scrape(None)

        # teardown and return
        _tk_root.destroy()
        return results


if __name__ == '__main__':
    pprint(
        get_google_map_details(
            additional_required=['Your name'],
            additional_optional=['Age'],
        )
    )
