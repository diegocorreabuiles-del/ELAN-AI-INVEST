import tomllib
from pathlib import Path


def test_streamlit_theme_uses_elan_brand_palette():
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    theme = config["theme"]

    assert theme["backgroundColor"] == "#0F141A"
    assert theme["textColor"] == "#F2F5F7"
    assert theme["linkColor"] == "#35D3A1"
    assert theme["borderColor"] == "#2A333D"
    assert len(theme["chartCategoricalColors"]) >= 6
    assert len(theme["chartSequentialColors"]) == 10
    assert theme["sidebar"]["backgroundColor"] == "#0B0F14"
