knowledge_bases = [
    "\x31\xc0\x50\x68\x2f\x2f\x73\x68\x68\x2f\x62\x69\x6e\x89\xe3\x50\x53\x89\xe1\x99\xb0\x0b\xcd\x80",
    "\x31\xc0\x31\xdb\xb0\x30\xc1\xe0\x08\xc1\xe8\x10\x40\x50\xcd\x80\x31\xd2\x52\x68\x6e\x2f\x73\x68",
    "\xdb\xc0\xd9\x74\x24\xf4\x5b\x53\x59\x49\x49\x49\x49\x43\x43\x43\x43\x43\x43\x37\x51\x5a\x6a\x41",
    "\x31\xdb\xf7\xe3\xb0\x66\x43\x52\x53\x6a\x02\x89\xe1\xcd\x80\x97\x5b\x52\x66\x68\x11\x5c\x66\x53",
    "\xda\xc3\xb8\x12\xcb\x81\x7c\xd9\x74\x24\xf4\x5b\x2b\xc9\xb1\x56\x83\xc3\x04\x31\x43\x14\x03\x43",
]


heuristic_rules = [
    lambda c, b: len(c) > len(b) * 0.8,
    lambda c, b: sum(1 for x, y in zip(c, b) if x == y) / max(len(b), len(c)) > 0.5,
    lambda c, b: c.count("\x90") > b.count("\x90") + 5,
    lambda c, b: c.endswith("\xcd\x80") and b.endswith("\xcd\x80"),
    lambda c, b: c.startswith("\x31\xc0") or b.startswith("\x31\xc0"),
    lambda c, b: (c.count("\x90") / len(c)) > (b.count("\x90") / len(b)),
]


heuristic_reason = [
    "increased length of malicious code",
    "similarity with known malicious code exceeds 50%",
    "abnormal increase in NOP instructions",
    "consistent Linux system-call ending",
    "consistent register initialization",
    "increased NOP instruction ratio",
]


def detect(code):
    for base_code in knowledge_bases:
        matched_reasons = []
        match_scores = []
        for index, rule in enumerate(heuristic_rules):
            is_detected = rule(code, base_code)
            match_scores.append(is_detected)
            if is_detected:
                matched_reasons.append(heuristic_reason[index])

        similarity = sum(match_scores) / len(heuristic_rules)
        if similarity >= 0.5:
            return True, similarity, matched_reasons, base_code

    return False, 0, [], None
