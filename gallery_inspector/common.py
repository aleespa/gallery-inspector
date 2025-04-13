import re


def clean_excel_unsafe(val):
    if isinstance(val, str):
        return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', val)
    return val


def rational_to_float(r):
    try:
        return float(r)
    except Exception:
        return None