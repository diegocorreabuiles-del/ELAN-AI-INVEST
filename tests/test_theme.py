import tomllib
from pathlib import Path


def test_streamlit_theme_uses_elan_brand_palette():
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    theme = config["theme"]

    assert theme["backgroundColor"] == "#141654"
    assert theme["textColor"] == "#D8B511"
    assert theme["linkColor"] == "#F2D34F"
    assert len(theme["chartCategoricalColors"]) >= 6
    assert len(theme["chartSequentialColors"]) == 10
    assert theme["sidebar"]["backgroundColor"] == "#0E103C"
