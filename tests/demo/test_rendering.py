from demo.lib.rendering import money, status_badge


def test_money_formats_decimal_strings() -> None:
    assert money("1200") == "$1,200.00"
    assert money("1200.5") == "$1,200.50"


def test_status_badge_humanizes_enum_values() -> None:
    assert status_badge("PARTIALLY_APPROVED") == "Partially Approved"
