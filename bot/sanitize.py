
import re


def sanitize_name(str):
    str = re.sub(r"[‘’`´′‛.']", "", str)
    str = re.sub(r"-", " ", str)
    return str
