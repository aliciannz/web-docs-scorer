import re
from typing import List


def join_utf_blocks(u_list: List[str], inverse: bool = False) -> re.Pattern[str]:
    inversion = "^" if inverse else ""
    prefixes = ["u", "U000"]
    pattern = f"[{inversion}"
    for x in u_list:
        prefix = prefixes[0] if len(x) == 9 else prefixes[1]
        cases = f'\\{prefix}{x.split("-")[0]}-\\{prefix}{x.split("-")[1]}'
        pattern = f"{pattern}{cases}"
    return re.compile(f"{pattern}]")


def custom_mean(neg_values: List[float]) -> float:
    # Negative values
    minor1 = min(neg_values)
    neg_values.remove(minor1)
    minor2 = min(neg_values)
    neg_values.remove(minor2)
    return minor1 * minor2 * (sum(neg_values) / len(neg_values))


def precision_round(number: float) -> float:
    number_str = str(number)
    first_digit_index = next(
        (i for i, d in enumerate(number_str) if d != "0" and d != "."), None
    )
    if first_digit_index is None:
        rounded_value = round(number, 1)
    else:
        to_round_digits = max(0, 1 - first_digit_index)
        rounded_value = round(number, to_round_digits)
    return rounded_value


def average(numbers: List[float]) -> float:
    return round(sum(numbers) / len(numbers), 3)
