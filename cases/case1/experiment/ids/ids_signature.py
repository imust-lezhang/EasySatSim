detection_rules = [
    "\x31\xc0\x50\x68\x2f\x2f\x73\x68",
    "\x31\xdb\xf7\xe3\xb0\x66",
]


def detect(code):
    for rule in detection_rules:
        if rule in code:
            return True, rule
    return False, None
