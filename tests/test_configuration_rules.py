from jarvis.domain.configuration import BuildStatus, VehicleBuild
from jarvis.rules.catalog_vocabulary import CatalogVocabulary
from jarvis.rules.configuration_validator import ConfigurationValidator


def violated_rule_ids(validator: ConfigurationValidator, build: VehicleBuild) -> list[str]:
    return [violation.rule_id for violation in validator.validate_build(build).violations]


def test_v8_with_manual_gearbox_is_rejected(configuration_validator: ConfigurationValidator) -> None:
    build = VehicleBuild(model="Ford F-350", engine="5.0L V8", transmission="6-Speed Manual", trim="Base")

    assert violated_rule_ids(configuration_validator, build) == ["RULE-V8-TRANSMISSION"]
    assert configuration_validator.validate_build(build).status is BuildStatus.INVALID


def test_f150_cannot_use_the_v8(configuration_validator: ConfigurationValidator) -> None:
    build = VehicleBuild(model="Ford F-150", engine="5.0L V8")

    assert violated_rule_ids(configuration_validator, build) == ["RULE-COMPAT-M1-E3"]


def test_electric_drivetrain_requires_direct_drive(configuration_validator: ConfigurationValidator) -> None:
    build = VehicleBuild(model="Ford F-150", engine="EV Dual Motor", transmission="10-Speed Automatic")

    assert violated_rule_ids(configuration_validator, build) == ["RULE-EV-TRANSMISSION"]


def test_complete_compatible_build_is_valid(configuration_validator: ConfigurationValidator) -> None:
    build = VehicleBuild(
        model="Ford F-350", engine="5.0L V8", transmission="10-Speed Automatic", trim="Premium"
    )

    result = configuration_validator.validate_build(build)

    assert result.status is BuildStatus.VALID
    assert result.missing_fields == []


def test_partial_build_is_incomplete_and_lists_missing_fields(
    configuration_validator: ConfigurationValidator,
) -> None:
    result = configuration_validator.validate_build(VehicleBuild(model="RAM 2500"))

    assert result.status is BuildStatus.INCOMPLETE
    assert result.missing_fields == ["engine", "transmission", "trim"]


def test_logging_application_returns_recommendation(configuration_validator: ConfigurationValidator) -> None:
    result = configuration_validator.validate_build(VehicleBuild(application="Logging"))

    assert [finding.rule_id for finding in result.recommendations] == ["RULE-LOGGING-RECOMMENDATION"]


def test_vocabulary_maps_informal_names_to_catalog_names(catalog_vocabulary: CatalogVocabulary) -> None:
    normalized = catalog_vocabulary.normalize_build(
        VehicleBuild(model="F-150", engine="V8", transmission="automatic", trim="None", application="logging")
    )

    assert normalized == VehicleBuild(
        model="Ford F-150",
        engine="5.0L V8",
        transmission="10-Speed Automatic",
        trim=None,
        application="Logging",
    )


def test_vocabulary_keeps_ambiguous_values_unchanged(catalog_vocabulary: CatalogVocabulary) -> None:
    assert catalog_vocabulary.normalize_build(VehicleBuild(model="Ford")).model == "Ford"


def test_merging_builds_keeps_previous_choices() -> None:
    previous_build = VehicleBuild(model="Ford F-350", engine="5.0L V8")

    merged = previous_build.merge_with(VehicleBuild(trim="Premium"))

    assert merged == VehicleBuild(model="Ford F-350", engine="5.0L V8", trim="Premium")
