"""CSV出力(F-10)。詳細設計書4.11.1章: UTF-8(BOM付き)・カンマ区切り・CRLF・数式実行の防止。"""
import csv
import io

BOM = "﻿"
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value  # 表計算ソフトでの数式実行を防ぐ(文字列のみ。数値は対象外)
    return value


class CsvWriter:
    @staticmethod
    def write(header: list[str], rows: list[list[object]]) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow([_sanitize(v) for v in row])
        return (BOM + buffer.getvalue()).encode("utf-8")
