import json
from pathlib import Path

INTEGRATION = Path(__file__).parents[1] / "custom_components" / "seltron_clausius"


def test_manifest_declares_narrow_cloud_polling_integration() -> None:
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["domain"] == "seltron_clausius"
    assert manifest["config_flow"] is True
    assert manifest["iot_class"] == "cloud_polling"
    assert manifest["version"] == "0.4.1"
    assert manifest["requirements"] == []
    assert not (INTEGRATION / "climate.py").exists()
    assert (INTEGRATION / "switch.py").exists()
    assert not (INTEGRATION / "button.py").exists()
    assert not (INTEGRATION / "services.yaml").exists()
