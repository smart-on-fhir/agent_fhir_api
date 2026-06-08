import re


def parse_file_name(filename: str) -> tuple[bool, str]:
    filename_pattern = re.compile(r"^([A-Z][a-zA-Z]+)\.\d{3}\.ndjson$")
    match = filename_pattern.match(filename)
    if not match:
        return False, ''
    return True, match.group(1)