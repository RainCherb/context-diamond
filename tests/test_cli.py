from processpilot import cli


def test_cli_binds_to_loopback_by_default(monkeypatch):
    captured = {}

    def fake_run(app, **kwargs):
        captured["app"] = app
        captured.update(kwargs)

    monkeypatch.setattr(cli.uvicorn, "run", fake_run)
    cli.main()
    assert captured["app"] == "processpilot.api:app"
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8000
