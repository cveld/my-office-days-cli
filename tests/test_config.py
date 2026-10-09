from my_office_days.config import Config


def test_config_round_trip(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    Config(base_url="https://example.test", employee_guid="employee-1").save()

    assert Config.load().base_url == "https://example.test"
    assert Config.load().employee_guid == "employee-1"
