def extract_context_words(text):
    text = text.lower()
    return set(text.split())


def score_context(trigger, context_words):
    hint = trigger.get("context_hint", "")
    if not hint:
        return 0

    hint_words = set(hint.lower().split())

    overlap = len(context_words & hint_words)

    return overlap * 10


def apply_context_boost(matches, input_text):
    context_words = extract_context_words(input_text)

    for m in matches:
        trig = m["trigger"]

        boost = score_context(trig, context_words)

        if boost > 0:
            m["score"] = min(m["score"] + boost, 100)
            m.setdefault("reasons", []).append(f"context match boost (+{boost})")

    matches.sort(key=lambda x: x["score"], reverse=True)

    return matches