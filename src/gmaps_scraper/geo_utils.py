def is_state_in_country(state_name, country_code='US'):
    country = pycountry.countries.get(alpha_2=country_code)
    if country:
        # Get all subdivisions (states) within the United States
        subdivisions = list(pycountry.subdivisions.get(country_code=country.alpha_2))

        # Check if the state name matches any of the subdivisions
        matching_subdivisions = [subdivision for subdivision in subdivisions if subdivision.name == state_name]

        if len(matching_subdivisions) == 1:
            # print(f"{state_name} IS a state in {country.name}")
            return True
        elif len(matching_subdivisions) > 1:
            raise OverflowError(f"Multiple states with name {state_name} found in {country.name}")
        else:
            # print(f"{state_name} IS NOT a state in {country.name}")
            return False


def get_country_code(country_name):
    """
    Returns the alpha-2 code of a country.
    If no match is found, it raises a LookupError exception.

    :param country_name: country (has to be in the pycountry module)
    :return: The alpha-2 code of the country
    """
    not_found_msg = f"Country not found: {country_name}"
    try:
        # Search for the country by name
        country = pycountry.countries.search_fuzzy(country_name)
        if country:
            # Return the alpha-2 code of the first match
            return country[0].alpha_2
        # If country is not found, raise LookupError
        raise LookupError(not_found_msg)
    except LookupError as e:
        print_exception(e)
        print_error(not_found_msg)
        raise e
