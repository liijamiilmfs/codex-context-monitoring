from codex_context_monitoring.app import main


def test_main_starts_the_local_shell(capsys) -> None:
    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == (
        "Codex Context Monitoring is ready.\n"
        "Session data must be supplied manually; automatic Codex Desktop and "
        "CLI collection is out of scope for this MVP.\n"
    )
    assert captured.err == ""
