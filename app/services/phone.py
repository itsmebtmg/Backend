import re


class InvalidMoroccanPhone(ValueError):
    pass


def normalize_moroccan_phone(raw: str) -> dict[str, str]:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("212"):
        local = "0" + digits[3:]
    elif digits.startswith("0"):
        local = digits
    else:
        raise InvalidMoroccanPhone("invalid_moroccan_phone")

    if not re.fullmatch(r"0[567]\d{8}", local):
        raise InvalidMoroccanPhone("invalid_moroccan_phone")

    national_without_zero = local[1:]
    return {
        "local": local,
        "e164": "+212" + national_without_zero,
        "digits_international": "212" + national_without_zero,
    }
