import pycountry
from colorfulPyPrint.py_color import print_error, print_exception


def is_state_in_country(state_name: str, country_code: str = 'US') -> bool:
    country = pycountry.countries.get(alpha_2=country_code)
    if not country:
        return False
    subdivisions = list(pycountry.subdivisions.get(country_code=country.alpha_2))

    # Check if the state name matches any of the subdivisions
    matches = [s for s in subdivisions if s.name == state_name]
    if len(matches) > 1:
        raise OverflowError(f"Multiple states named {state_name} in {country.name}")
    return bool(matches)


def get_country_code(country_name: str) -> str:
    """
    Returns the alpha-2 code of a country.

    Args:
        country_name: country (has to be in the pycountry module)
    Returns:
        The alpha-2 code of the country
    Raises:
        LookupError if not match is found
    """
    try:
        results = pycountry.countries.search_fuzzy(country_name)
        return results[0].alpha_2
    except LookupError as e:
        print_exception(e)
        print_error(f"Country not found: {country_name}")
        raise
