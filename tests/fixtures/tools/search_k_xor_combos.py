#!/usr/bin/env python3
import argparse
import itertools
import json
import os
import sys
from collections import namedtuple

Candidate = namedtuple("Candidate", ["label", "value"])
Transform = namedtuple("Transform", ["name", "func", "rank"])

DEFAULT_K = 0x4A6E529D
DEFAULT_CANDIDATES = [
    Candidate("A", 0x69D1B2C0),
    Candidate("B", 0x6FDF6FC0),
    Candidate("T", 0x00040202),
    Candidate("C", 0x00000010),
    Candidate("S1", 0x05F5E100),
    Candidate("S2", 0x00000001),
    Candidate("G1", 0x001C09FF),
    Candidate("G2", 0x097DDBE0),
]

TRANSFORMS = [
    Transform("raw", lambda x: x & 0xFFFFFFFF, 0),
    Transform("byteswapped", lambda x: int.from_bytes((x & 0xFFFFFFFF).to_bytes(4, "little"), "big"), 1),
    Transform("not", lambda x: (~x) & 0xFFFFFFFF, 2),
    Transform("low16", lambda x: (x & 0xFFFF), 3),
    Transform("high16", lambda x: ((x >> 16) & 0xFFFF), 4),
]


class CandidateItem:
    def __init__(self, label, transform_name, value, base_label, transform_rank):
        self.label = label
        self.transform_name = transform_name
        self.value = value
        self.base_label = base_label
        self.transform_rank = transform_rank

    def token(self):
        return f"{self.base_label}:{self.transform_name}"

    def __repr__(self):
        return f"CandidateItem({self.token()}=0x{self.value:08X})"


def build_items(candidates, include_transforms):
    items = []
    for cand in candidates:
        if include_transforms:
            for transform in TRANSFORMS:
                items.append(CandidateItem(
                    label=cand.label,
                    transform_name=transform.name,
                    value=transform.func(cand.value),
                    base_label=cand.label,
                    transform_rank=transform.rank,
                ))
        else:
            raw = TRANSFORMS[0]
            items.append(CandidateItem(
                label=cand.label,
                transform_name=raw.name,
                value=raw.func(cand.value),
                base_label=cand.label,
                transform_rank=raw.rank,
            ))
    return items


def parse_candidate_file(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Candidate file not found: {path}")

    candidates = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return candidates
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                for label, raw in data.items():
                    candidates.append(Candidate(label, int(raw, 0) if isinstance(raw, str) else int(raw)))
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "label" in item and "value" in item:
                        candidates.append(Candidate(item["label"], int(item["value"], 0) if isinstance(item["value"], str) else int(item["value"])))
                    else:
                        raise ValueError("Candidate file list items must be objects with label and value")
            else:
                raise ValueError("Candidate file must be JSON object or array")
        except json.JSONDecodeError:
            for line in content.splitlines():
                token = line.strip().split()
                if not token:
                    continue
                if len(token) == 1:
                    label = f"V{len(candidates)+1}"
                    value = int(token[0], 0)
                else:
                    label = token[0]
                    value = int(token[1], 0)
                candidates.append(Candidate(label, value))
    return candidates


def popcount(value):
    return bin(value & 0xFFFFFFFF).count("1")


def score_combo(combo):
    num_terms = len(combo)
    transform_penalty = sum(item.transform_rank for item in combo)
    label_rank = sum(len(item.base_label) for item in combo)
    return (num_terms, transform_penalty, label_rank)


def format_combo(combo):
    pieces = []
    for item in combo:
        if item.transform_name == "raw":
            pieces.append(f"{item.base_label}")
        else:
            pieces.append(f"{item.base_label}.{item.transform_name}")
    return " ^ ".join(pieces)


def search_combinations(items, target, max_terms, max_results=1000):
    unique_results = {}
    best_residuals = []
    seen_combos = set()

    for term_count in range(1, max_terms + 1):
        for combo in itertools.combinations(items, term_count):
            labels = tuple(sorted(item.token() for item in combo))
            if labels in seen_combos:
                continue
            seen_combos.add(labels)
            result = 0
            for item in combo:
                result ^= item.value
            if result == target:
                score = score_combo(combo)
                unique_results[labels] = (combo, score, result, 0)
            else:
                residual = result ^ target
                distance = popcount(residual)
                best_residuals.append((distance, residual, combo, result))
    exact = sorted(unique_results.values(), key=lambda x: x[1])
    best_partial = sorted(best_residuals, key=lambda r: (r[0], popcount(r[1]), len(r[2]), score_combo(r[2])))[:20]
    return exact, best_partial


def main():
    parser = argparse.ArgumentParser(description="Search XOR combinations of candidate 32-bit words to match a target K value.")
    parser.add_argument("--k", default=f"0x{DEFAULT_K:08X}", help="Target K value in hex or decimal. Default is 4A6E529D.")
    parser.add_argument("--candidate-file", help="Optional candidate definition file (JSON or space-separated label value lines).")
    parser.add_argument("--max-terms", type=int, default=6, help="Maximum number of terms to combine. Default is 6.")
    parser.add_argument("--no-transforms", action="store_true", help="Disable transformed variants and use raw values only.")
    parser.add_argument("--top-partial", type=int, default=10, help="Number of nearest partial matches to report if no exact match is found.")
    args = parser.parse_args()

    target = int(args.k, 0)
    if args.candidate_file:
        candidates = parse_candidate_file(args.candidate_file)
    else:
        candidates = DEFAULT_CANDIDATES

    items = build_items(candidates, include_transforms=not args.no_transforms)
    if not items:
        print("No candidates available. Use --candidate-file or add candidates.")
        sys.exit(1)

    exact, partial = search_combinations(items, target, args.max_terms, max_results=args.top_partial)

    print("Target K:", f"0x{target:08X}")
    print("Candidates:")
    for cand in candidates:
        print(f"  {cand.label}: 0x{cand.value:08X}")
    print(f"Transforms enabled: {not args.no_transforms}")
    print(f"Search max terms: {args.max_terms}\n")

    if exact:
        print("Exact matches found:")
        for combo, score, result, residual in exact:
            print(f"- {format_combo(combo)} = 0x{result:08X} ({len(combo)} terms)")
        first = exact[0]
        combo, score, result, residual = first
        print("\nBest exact match:")
        print(f"  {format_combo(combo)} = 0x{result:08X}")
        print(f"  terms: {len(combo)}")
    else:
        print("No exact match found.")
        print(f"Nearest partial matches (top {args.top_partial}):")
        for distance, residual, combo, result in partial[: args.top_partial]:
            print(f"- {format_combo(combo)} => 0x{result:08X}, residual=0x{residual:08X}, hamming={distance}, terms={len(combo)}")

    sys.exit(0)


if __name__ == "__main__":
    main()
