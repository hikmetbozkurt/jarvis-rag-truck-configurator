from pathlib import Path

from jarvis.domain.configuration import (
    REQUIRED_BUILD_FIELDS,
    BuildStatus,
    BuildValidationResult,
    CompatibilityRule,
    RuleFinding,
    RuleType,
    VehicleBuild,
)
from jarvis.ingestion.document_sources import read_json_dataset
from jarvis.rules.catalog_vocabulary import compact_catalog_term


def _is_same_catalog_term(first_value: str | None, second_value: str) -> bool:
    return first_value is not None and compact_catalog_term(first_value) == compact_catalog_term(second_value)


class ConfigurationValidator:
    """Checks a build against the catalog rules in code, so constraints never depend on the LLM."""

    def __init__(self, rules: list[CompatibilityRule]) -> None:
        self._rules = rules

    @classmethod
    def from_catalog_file(cls, catalog_path: Path) -> "ConfigurationValidator":
        catalog = read_json_dataset(catalog_path)
        return cls([CompatibilityRule.model_validate(rule) for rule in catalog["rules"]])

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def validate_build(self, build: VehicleBuild) -> BuildValidationResult:
        violations: list[RuleFinding] = []
        recommendations: list[RuleFinding] = []

        for rule in self._rules:
            if not self._are_conditions_met(rule, build):
                continue
            finding = RuleFinding(rule_id=rule.rule_id, rule_type=rule.rule_type, message=rule.message)
            if rule.rule_type is RuleType.RECOMMENDATION:
                recommendations.append(finding)
            elif self._is_constraint_broken(rule, build):
                violations.append(finding)

        missing_fields = [
            field_name for field_name in REQUIRED_BUILD_FIELDS if build.read_field(field_name) is None
        ]
        if violations:
            status = BuildStatus.INVALID
        elif missing_fields:
            status = BuildStatus.INCOMPLETE
        else:
            status = BuildStatus.VALID

        return BuildValidationResult(
            status=status,
            missing_fields=missing_fields,
            violations=violations,
            recommendations=recommendations,
        )

    @staticmethod
    def _are_conditions_met(rule: CompatibilityRule, build: VehicleBuild) -> bool:
        return all(
            _is_same_catalog_term(build.read_field(field_name), expected_value)
            for field_name, expected_value in rule.conditions.items()
        )

    @staticmethod
    def _is_constraint_broken(rule: CompatibilityRule, build: VehicleBuild) -> bool:
        uses_forbidden_option = bool(rule.forbidden) and all(
            _is_same_catalog_term(build.read_field(field_name), forbidden_value)
            for field_name, forbidden_value in rule.forbidden.items()
        )
        misses_required_option = any(
            build.read_field(field_name) is not None
            and not _is_same_catalog_term(build.read_field(field_name), required_value)
            for field_name, required_value in rule.required.items()
        )
        return uses_forbidden_option or misses_required_option
