"""Định dạng số độc lập với các mô-đun phân tích và pandas."""
import re

_SEP_IN_NUMBER = re.compile(r"(?<=\d)[.,](?=\d)")


def vn_digits(text: str) -> str:
    return _SEP_IN_NUMBER.sub(lambda m: "," if m.group(0) == "." else ".", text)
