from pathlib import Path

from elan_ai_invest.core.config import Settings
from elan_ai_invest.system_status import collect_system_status


def test_system_status_reports_required_files(tmp_path: Path):
    (tmp_path / "config").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "config" / "settings.yaml").write_text("app: {}", encoding="utf-8")
    (tmp_path / "config" / "watchlist.csv").write_text(
        "symbol,name\nSPY,S&P 500\n", encoding="utf-8"
    )
    status = collect_system_status(tmp_path, Settings())
    assert status.ok
    assert status.version == "0.7.0"
