def validate_numeral(new_text: str):
    if (new_text.startswith("-")):
        new_text = new_text[1:]
    return new_text.isnumeric()

def validate_numeral_non_negative(new_text: str):
    return new_text.isnumeric()

def validate_null(_: str): return True
