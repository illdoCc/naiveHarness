"""CSV Parser 修復練習：這份起始程式刻意保留 bug。

輸入都是合法的單行 CSV，不包含多行欄位，也不必處理格式錯誤。
逗號分隔欄位，但完整 quoted field 裡的逗號屬於內容。
quoted field 內的兩個連續雙引號代表一個雙引號。
請保留空欄位與前後空白；空輸入也應回傳一個空欄位。
修復時不能直接使用 Python csv library。
"""


def parse_csv(line: str) -> list[str]:
    """逐字讀取欄位；這是刻意保留邊界錯誤的起始版本。"""
    result = []
    field = ""
    in_quotes = False

    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == ',' and not in_quotes:
            result.append(field)
            field = ""
        else:
            field += ch

    if field:
        result.append(field)

    return result
