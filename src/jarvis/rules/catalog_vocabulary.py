import re
from pathlib import Path

from jarvis.domain.configuration import VehicleBuild
from jarvis.ingestion.document_sources import read_json_dataset

_PLACEHOLDER_VALUES = frozenset({"", "none", "null", "n/a", "na", "tbd", "unknown", "not selected"})
_CATALOG_SECTIONS_BY_BUILD_FIELD = {
    "model": "models",
    "engine": "engines",
    "transmission": "transmissions",
    "trim": "trims",
    "application": "applications",
}


def compact_catalog_term(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


class CatalogVocabulary:
    def __init__(self, option_names_by_field: dict[str, list[str]]) -> None:
        self._option_names_by_field = option_names_by_field

    @classmethod
    def from_catalog_file(cls, catalog_path: Path) -> "CatalogVocabulary":
        catalog = read_json_dataset(catalog_path)
        return cls(
            {
                build_field: [option["name"] for option in catalog[catalog_section]]
                for build_field, catalog_section in _CATALOG_SECTIONS_BY_BUILD_FIELD.items()
            }
        )

    def list_option_names(self, build_field: str) -> list[str]:
        return list(self._option_names_by_field.get(build_field, []))

    def normalize_build(self, build: VehicleBuild) -> VehicleBuild:
        normalized_values: dict[str, str | None] = {}
        for build_field, raw_value in build.model_dump().items():
            if raw_value is None or raw_value.strip().lower() in _PLACEHOLDER_VALUES:
                normalized_values[build_field] = None
            else:
                normalized_values[build_field] = self._find_catalog_name(build_field, raw_value.strip())
        return VehicleBuild(**normalized_values)

    def _find_catalog_name(self, build_field: str, raw_value: str) -> str:
        compact_value = compact_catalog_term(raw_value)
        option_names = self._option_names_by_field.get(build_field, [])

        for option_name in option_names:
            if compact_catalog_term(option_name) == compact_value:
                return option_name

        partial_matches = [
            option_name
            for option_name in option_names
            if compact_catalog_term(option_name) in compact_value
            or (len(compact_value) >= 2 and compact_value in compact_catalog_term(option_name))
        ]
        return partial_matches[0] if len(partial_matches) == 1 else raw_value
