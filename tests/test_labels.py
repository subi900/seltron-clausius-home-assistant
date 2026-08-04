import pytest

from custom_components.seltron_clausius.labels import (
    channel_label,
    normalize_labels,
)


def test_channel_label_uses_user_override_without_changing_channel_identity() -> None:
    options = {
        "labels": {
            "relay:R1": "Umlaufpumpe der Gasheizung",
            "temperature:T2": "Außentemperatur",
        }
    }

    assert channel_label(options, "relay", "R1", "R1") == "Umlaufpumpe der Gasheizung"
    assert channel_label(options, "temperature", "T2", "T2") == "Außentemperatur"
    assert channel_label(options, "relay", "R2", "R2") == "R2"


def test_normalize_labels_strips_values_and_discards_blank_fallbacks() -> None:
    labels = normalize_labels(
        {
            "relay:R1": "  Umlaufpumpe der Gasheizung  ",
            "relay:R2": "   ",
            "temperature:T2": "Außentemperatur",
        }
    )

    assert labels == {
        "relay:R1": "Umlaufpumpe der Gasheizung",
        "temperature:T2": "Außentemperatur",
    }


@pytest.mark.parametrize("value", ["bad\nlabel", "bad\tlabel", "x" * 81])
def test_normalize_labels_rejects_unsafe_values(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_labels({"relay:R1": value})


def test_normalize_labels_accepts_only_known_namespaces_and_codes() -> None:
    with pytest.raises(ValueError):
        normalize_labels({"unknown:R1": "Label"})
    with pytest.raises(ValueError):
        normalize_labels({"relay:R1/escape": "Label"})
