import csv
import os
import re


def normalize(text):
    if text is None:
        return ""
    text = str(text).strip().lower()
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


class TriggerMatcher:
    def __init__(self, csv_path):
        self.triggers = []
        self.load(csv_path)

    def load(self, csv_path):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Trigger CSV not found: {csv_path}")

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.triggers.append(row)

    def _safe_words(self, text):
        norm = normalize(text)
        if not norm:
            return set()
        return set(norm.split())

    def _split_aliases(self, raw_aliases):
        if raw_aliases is None:
            return []
        return [normalize(x) for x in str(raw_aliases).split("|") if normalize(x)]

    def _score_candidate(self, input_norm, input_words, trig):
        score = 0
        reasons = []

        trig_text = normalize(trig.get("trigger_text", ""))
        alias_list = self._split_aliases(trig.get("alias_texts", trig.get("alias_text", "")))
        context_hint = normalize(trig.get("context_hint", ""))

        trig_words = self._safe_words(trig_text)
        context_words = self._safe_words(context_hint)

        # Exact trigger
        if input_norm == trig_text:
            score = max(score, 100)
            reasons.append("exact trigger match")

        # Trigger contains / contained by
        if trig_text and trig_text in input_norm:
            score = max(score, 88)
            reasons.append("trigger phrase found in input")

        if trig_text and input_norm in trig_text:
            score = max(score, 84)
            reasons.append("input found inside trigger phrase")

        # Alias checks
        best_alias_score = 0
        best_alias_reason = None

        for alias in alias_list:
            if input_norm == alias:
                if 98 > best_alias_score:
                    best_alias_score = 98
                    best_alias_reason = f"exact alias match: {alias}"

            elif alias and alias in input_norm:
                if 82 > best_alias_score:
                    best_alias_score = 82
                    best_alias_reason = f"alias phrase found in input: {alias}"

            elif alias and input_norm in alias:
                if 80 > best_alias_score:
                    best_alias_score = 80
                    best_alias_reason = f"input found inside alias: {alias}"

            else:
                alias_words = self._safe_words(alias)
                alias_overlap = len(input_words & alias_words)
                if alias_overlap > 0:
                    alias_score = 56 + (alias_overlap * 10)
                    if alias_score > best_alias_score:
                        best_alias_score = alias_score
                        best_alias_reason = f"word overlap with alias: {alias}"

        if best_alias_score > 0:
            score = max(score, best_alias_score)
            reasons.append(best_alias_reason)

        # Trigger word overlap
        trig_overlap = len(input_words & trig_words)
        if trig_overlap > 0:
            overlap_score = 58 + (trig_overlap * 10)
            if overlap_score > score:
                score = overlap_score
            reasons.append(f"word overlap with trigger ({trig_overlap})")

        # Context boost
        context_overlap = len(input_words & context_words)
        if context_overlap > 0:
            score = max(score, min(score + (context_overlap * 4), 100))
            reasons.append(f"context boost ({context_overlap})")

        # Priority boost
        try:
            priority = int(trig.get("priority", 0))
        except Exception:
            priority = 0

        priority_boost = min(priority // 20, 5)
        if priority_boost > 0 and score > 0:
            score = min(score + priority_boost, 100)
            reasons.append(f"priority boost (+{priority_boost})")

        return score, reasons

    def match(self, input_text):
        input_norm = normalize(input_text)
        input_words = self._safe_words(input_norm)

        results = []

        for trig in self.triggers:
            score, reasons = self._score_candidate(input_norm, input_words, trig)

            if score > 0:
                results.append({
                    "trigger": trig,
                    "score": score,
                    "reasons": reasons
                })

        results.sort(key=lambda x: x["score"], reverse=True)

        deduped = []
        seen_keys = set()

        for item in results:
            path = item["trigger"].get("target_path", "")
            trig_text = item["trigger"].get("trigger_text", "")
            key = (path, trig_text)

            if key in seen_keys:
                continue

            seen_keys.add(key)
            deduped.append(item)

        return deduped