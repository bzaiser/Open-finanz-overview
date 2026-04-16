from decimal import Decimal

def safe_float(val, default=0.0):
    """Safely converts a value (string, None, Decimal, etc.) to float."""
    if val is None or val == "":
        return default
    try:
        if isinstance(val, str):
            # Handle German decimal comma
            val = val.replace(',', '.')
            # Remove any non-numeric characters except . and -
            val = "".join(c for c in val if c.isdigit() or c in '.-')
            if not val or val == '.' or val == '-':
                return default
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    """Safely converts a value to int."""
    if val is None or val == "":
        return default
    try:
        if isinstance(val, str):
            val = "".join(c for c in val if c.isdigit() or c == '-')
            if not val or val == '-':
                return default
        return int(float(val))
    except (ValueError, TypeError):
        return default
