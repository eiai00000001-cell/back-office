"""CsvWriter(F-10、詳細設計書4.11.1章)。"""
from app.utils.csv_writer import CsvWriter


def _decode(data: bytes) -> str:
    assert data.startswith(b"\xef\xbb\xbf")
    return data[3:].decode("utf-8")


def test_writes_bom_header_and_crlf():
    data = CsvWriter.write(["a", "b"], [["x", 1], ["y", 2]])
    assert _decode(data) == "a,b\r\nx,1\r\ny,2\r\n"


def test_header_only_when_no_rows():
    assert _decode(CsvWriter.write(["a", "b"], [])) == "a,b\r\n"


def test_quotes_values_with_comma_newline_and_quote():
    data = _decode(CsvWriter.write(["m"], [["a,b"], ['say "hi"'], ["l1\nl2"]]))
    assert data == 'm\r\n"a,b"\r\n"say ""hi"""\r\n"l1\nl2"\r\n'


def test_none_becomes_empty():
    assert _decode(CsvWriter.write(["a", "b"], [[None, "x"]])) == "a,b\r\n,x\r\n"


def test_formula_prefix_is_neutralised_for_strings_only():
    data = _decode(CsvWriter.write(["m"], [["=SUM(A1)"], ["+1"], ["-x"], ["@a"], [-12000], ["普通"]]))
    lines = data.split("\r\n")
    assert lines[1:7] == ["'=SUM(A1)", "'+1", "'-x", "'@a", "-12000", "普通"]


def test_japanese_text_is_utf8():
    assert "請求書".encode("utf-8") in CsvWriter.write(["請求書"], [])


def test_leading_tab_and_cr_are_neutralised():
    data = _decode(CsvWriter.write(["m"], [["\tabc"], ["\rabc"]]))
    assert data == "m\r\n'\tabc\r\n\"'\rabc\"\r\n"


def test_numeric_values_are_never_prefixed():
    from decimal import Decimal

    data = _decode(CsvWriter.write(["a", "b", "c"], [[-12000, Decimal("-1.5"), -0.5]]))
    assert data == "a,b,c\r\n-12000,-1.5,-0.5\r\n"
    assert _decode(CsvWriter.write(["a"], [["-12000"]])) == "a\r\n'-12000\r\n"
