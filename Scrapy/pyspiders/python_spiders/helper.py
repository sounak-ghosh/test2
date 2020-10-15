import re
from datetime import datetime


def string_found(_word_list, _description):
    _description = _description.lower()
    for _word in _word_list:
        if re.search(r"\b" + re.escape(_word.lower()) + r"\b", _description):
            return True
    return False

def remove_white_spaces(input_string):
    """
    Removes continuous spaces in the input string
    :param input_string:
    """
    return re.sub(r'\s+', ' ', input_string).strip()


def remove_unicode_char(input_string):
    """
    This function takes string as an input, and return strings after removing unicode character
    """
    return (''.join([i if ord(i) < 128 else ' ' for i in input_string])).strip()


def extract_number_only(input_string):
    """[This function is used to extract number from string, Common usecase is extract rent and square feet]

    Args:
        input_string ([type]): [should be string that have string + Numbers]

    Returns:
        [type]: [numbers from string ]
    """
    return (''.join(filter(lambda i: i.isdigit(), remove_white_spaces(input_string)))).strip()


def currency_parser(input_string):
    """[This function exttract currency type from Rent or any other field that has unicode symbol]

    Args:
        input_string ([string]): [String with currency symbol]

    Returns:
        [string]: [Currency]
    """
    currency = None
    if u'\u20ac' in input_string:
        currency = 'EUR'
    elif u'\xa3' in input_string:
        currency = 'GBP'
    elif '$' in input_string:
        currency = 'USD'
    return currency


def format_date(input_string, date_format="%d/%m/%Y"):
    """[This function convert date from String version to python date object]

    Args:
        input_string ([string]): [String representation of date]
        date_format (str, optional): [Pass date format if default is not the case]. Defaults to "%d/%m/%Y".

    Returns:
        [python date object]: [date]
    """
    try:
        return datetime.strptime(input_string, date_format).strftime("%Y-%m-%d")
    except Exception as e:
        print(e)
        return input_string

"""
This lookup is used to identify property_type by different language
"""
property_type_lookup = {
    'Appartements': 'apartment',
    'apartment': 'apartment',
    'Appartement': 'apartment',
    'Huis': 'house',
    'Woning': 'house'
}

def extract_rent_currency(_input_string):
    _new_input_string = remove_unicode_char(_input_string.replace('.', ''))
    _rent = extract_number_only(_new_input_string)
    if _rent:
        _rent = int(_rent)
    _currency = currency_parser(_input_string)
    return _rent, _currency

def square_meters_extract(_input_string):
    return extract_number_only(remove_unicode_char(_input_string))