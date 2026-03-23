def check_required_certificates(required, available):

    available_names = {c["name"].lower() for c in available}

    result = []

    for cert in required:
        name = cert.strip()
        if not name:
            continue

        if name.lower() in available_names:
            result.append((name, True))
        else:
            result.append((name, False))

    return result