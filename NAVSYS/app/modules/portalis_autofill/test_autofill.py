from trigger_matcher import TriggerMatcher
from value_resolver import ValueResolver
from confidence_engine import classify
from context_resolver import apply_context_boost

CSV_PATH = r"D:\NAVSYS_USB\data\PORTALIS\trigger_library.csv"

PORTALIS_DATA = {
    "crew": {
        "passport": {
            "number": "A1234567",
            "expiry_date": "2028-05-01"
        },
        "seaman_book": {
            "number": "SB998877",
            "expiry_date": "2029-11-30"
        },
        "visa": {
            "number": "USVISA7788",
            "expiry_date": "2027-08-15",
            "type": "C1/D"
        },
        "nationality": "GREECE",
        "date_of_birth": "1995-04-12",
        "place_of_birth": "PIRAEUS",
        "rank": "THIRD OFFICER",
        "gender": "M"
    },
    "ship": {
        "imo": "9876543",
        "name": "MV ASTRA",
        "flag": "GREECE",
        "call_sign": "SVAZ",
        "mmsi": "240123456",
        "gross_tonnage": "112345",
        "deadweight": "95600",
        "master": "CPT N. EXAMPLE",
        "operator": "ASTRA SHIPPING"
    },
    "voyage": {
        "last_port": "SABINE PASS",
        "next_port": "BARCARENA",
        "eta": "2026-03-25 12:00",
        "etd": "2026-03-26 18:00",
        "arrival": "2026-03-25 12:00",
        "agent": "PORT AGENCY EXAMPLE"
    },
    "cargo": {
        "type": "LNG",
        "quantity": "145000",
        "temperature": "-160",
        "boil_off_rate": "0.12"
    }
}


matcher = TriggerMatcher(CSV_PATH)
resolver = ValueResolver(PORTALIS_DATA)

while True:
    user_input = input("\nEnter field label: ").strip()

    if not user_input:
        continue

    if user_input.lower() in ["quit", "exit", "q"]:
        break

    matches = matcher.match(user_input)
    matches = apply_context_boost(matches, user_input)

    if not matches:
        print("No matches found.")
        continue

    print("\nTop matches:")
    print("-" * 80)

    for i, m in enumerate(matches[:5], start=1):
        trig = m["trigger"]
        score = m["score"]
        reasons = m.get("reasons", [])

        value = resolver.resolve(trig["target_path"])
        confidence = classify(score)

        print(f"[{i}] Trigger      : {trig['trigger_text']}")
        print(f"    Aliases      : {trig.get('alias_texts', trig.get('alias_text', ''))}")
        print(f"    Value        : {value}")
        print(f"    Confidence   : {confidence} ({score})")
        print(f"    Path         : {trig['target_path']}")
        print(f"    Context Hint : {trig.get('context_hint', '')}")
        print(f"    Reasons      : {', '.join(reasons) if reasons else 'n/a'}")
        print("-" * 80)