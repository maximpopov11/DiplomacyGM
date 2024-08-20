def extract_value(string, key):
    pairs = string.split(";")
    for pair in pairs:
        k, v = pair.split(":")
        if k == key:
            return v
