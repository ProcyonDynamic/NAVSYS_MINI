from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass(slots=True)
class CanonicalMappingResult:
    mapped_fields: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class CanonicalMapper:
    NATIONALITY_NORMALIZATION = {
        "PL": "POLISH",
        "POLAND": "POLISH",
        
        "GR": "GREEK",
        "GREECE": "GREEK",
        
        "PH": "FILIPINO",
        "PHILIPPINES": "FILIPINO",
        
        "UA": "UKRAINIAN",
        "UKRAINE": "UKRAINIAN",
        
        "IN": "INDIAN",
        "INDIA": "INDIAN",
        
        "RU": "RUSSIAN",
        "RUSSIA": "RUSSIAN",

        "CN": "CHINESE",
        "CHINA": "CHINESE",

        "VN": "VIETNAMESE",
        "VIETNAM": "VIETNAMESE",

        "ID": "INDONESIAN",
        "INDONESIA": "INDONESIAN",

        "TR": "TURKISH",
        "TURKEY": "TURKISH",

        "RO": "ROMANIAN",
        "ROMANIA": "ROMANIAN",

        "BG": "BULGARIAN",
        "BULGARIA": "BULGARIAN",

        "HR": "CROATIAN",
        "CROATIA": "CROATIAN",

        "RS": "SERBIAN",
        "SERBIA": "SERBIAN",

        "ME": "MONTENEGRIN",
        "MONTENEGRO": "MONTENEGRIN",

        "GE": "GEORGIAN",
        "GEORGIA": "GEORGIAN",

        "BD": "BANGLADESHI",
        "BANGLADESH": "BANGLADESHI",

        "MM": "MYANMAR",
        "MYANMAR": "MYANMAR",

        "PK": "PAKISTANI",
        "PAKISTAN": "PAKISTANI",

        "LK": "SRI LANKAN",
        "SRI LANKA": "SRI LANKAN",
        
        "DE": "GERMAN",
        "GERMANY": "GERMAN",

        "FR": "FRENCH",
        "FRANCE": "FRENCH",

        "IT": "ITALIAN",
        "ITALY": "ITALIAN",

        "ES": "SPANISH",
        "SPAIN": "SPANISH",

        "PT": "PORTUGUESE",
        "PORTUGAL": "PORTUGUESE",

        "NL": "DUTCH",
        "NETHERLANDS": "DUTCH",

        "BE": "BELGIAN",
        "BELGIUM": "BELGIAN",

        "SE": "SWEDISH",
        "SWEDEN": "SWEDISH",

        "DK": "DANISH",
        "DENMARK": "DANISH",

        "FI": "FINNISH",
        "FINLAND": "FINNISH",

        "EE": "ESTONIAN",
        "ESTONIA": "ESTONIAN",

        "LV": "LATVIAN",
        "LATVIA": "LATVIAN",

        "LT": "LITHUANIAN",  
        "LITHUANIA": "LITHUANIAN",

        "SI": "SLOVENIAN",
        "SLOVENIA": "SLOVENIAN",

        "SK": "SLOVAK",
        "SLOVAKIA": "SLOVAK",

        "CZ": "CZECH",
        "CZECHIA": "CZECH",
        "CZECH REPUBLIC": "CZECH",

        "AT": "AUSTRIAN",
        "AUSTRIA": "AUSTRIAN",

        "HU": "HUNGARIAN",
        "HUNGARY": "HUNGARIAN",

        "IE": "IRISH",
        "IRELAND": "IRISH",
        
        "CY": "CYPRIOT",
        "CYP": "CYPRIOT",
        "CYPRUS": "CYPRIOT",
        "CYPRIOT": "CYPRIOT",
    }

    DATE_FORMATS = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%d %b %Y",
        "%d %B %Y",
    ]

    def map_fields(self, extracted_fields: Dict[str, str]) -> CanonicalMappingResult:
        result = CanonicalMappingResult()

        for key, value in extracted_fields.items():
            cleaned = self._clean_value(value)

            if key in {
                "crew.date_of_birth",
                "passport.issue_date",
                "passport.expiry_date",
                "seaman_book.expiry_date",
                "vaccination.yellow_fever.issue_date",
                "vaccination.yellow_fever.expiry_date",
                "certificate.tonnage.issue_date",
                "certificate.tonnage.expiry_date",
            }:
                normalized = self._normalize_date(cleaned)
                if normalized:
                    result.mapped_fields[key] = normalized
                else:
                    result.mapped_fields[key] = cleaned
                    result.warnings.append(f"Could not normalize date for {key}: {cleaned}")
                continue

            if key in {"crew.nationality", "passport.issue_state", "seaman_book.issuing_state"}:
                result.mapped_fields[key] = self._normalize_nationality(cleaned)
                continue

            result.mapped_fields[key] = cleaned

        return result

    def _clean_value(self, value: str) -> str:
        return " ".join((value or "").strip().split())

    def _normalize_nationality(self, value: str) -> str:
        upper = value.upper().strip()

        # direct match
        if upper in self.NATIONALITY_NORMALIZATION:
            return self.NATIONALITY_NORMALIZATION[upper]

        # contains match
        for key, normalized in self.NATIONALITY_NORMALIZATION.items():
            if key in upper:
                return normalized

        return upper
    
    def _normalize_date(self, value: str) -> Optional[str]:
        text = value.strip()

        for fmt in self.DATE_FORMATS:
            try:
                dt = datetime.strptime(text, fmt)
                return dt.date().isoformat()
            except ValueError:
                continue

        return None