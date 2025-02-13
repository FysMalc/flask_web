def find_key(row, target_key):
    target_key = target_key.strip()
    for key in row.keys():
        if key.strip() == target_key:
            return key
    return None