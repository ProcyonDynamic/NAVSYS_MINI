def classify(score):
    if score >= 95:
        return "HIGH"
    elif score >= 80:
        return "MEDIUM"
    elif score >= 60:
        return "LOW"
    else:
        return "UNKNOWN"