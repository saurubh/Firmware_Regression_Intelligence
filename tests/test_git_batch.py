from fri.utils.git_batch import parse_name_only_log


def test_parse_name_only_log():
    output = (
        "COMMIT:aaa111\n"
        "MdeModulePkg/Bds.c\n"
        "README.md\n"
        "\n"
        "COMMIT:bbb222\n"
        "Fsp/Fsp.fd\n"
    )
    mapping = parse_name_only_log(output)
    assert mapping["aaa111"] == ["MdeModulePkg/Bds.c", "README.md"]
    assert mapping["bbb222"] == ["Fsp/Fsp.fd"]


def test_parse_name_only_log_empty():
    assert parse_name_only_log("") == {}
