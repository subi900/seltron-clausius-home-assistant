import json
from pathlib import Path

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "seltron_clausius"


def test_option_translation_keys_match_source_strings() -> None:
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    expected_data_keys = set(strings["options"]["step"]["init"]["data"])
    expected_error_keys = set(strings["options"]["error"])

    for language in ("de", "en"):
        translation = json.loads(
            (INTEGRATION / "translations" / f"{language}.json").read_text(
                encoding="utf-8"
            )
        )
        assert set(translation["options"]["step"]["init"]["data"]) == (
            expected_data_keys
        )
        assert set(translation["options"]["error"]) == expected_error_keys
        assert set(translation["config"]["step"]) == set(strings["config"]["step"])
        assert set(translation["config"]["abort"]) == set(strings["config"]["abort"])
        for step in ("user", "reauth_confirm", "reconfigure"):
            assert set(translation["config"]["step"][step]["data"]) == {"email", "password"}
