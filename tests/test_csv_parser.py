"""固定測試：從專案根目錄執行 python -m unittest discover -s tests -p test_csv_parser.py -v。

十個案例涵蓋主要 CSV 規則；起始程式應有測試失敗，請修程式而不是修改預期答案。
"""
import unittest
from csv_parser import parse_csv

class TestCSVParser(unittest.TestCase):
    """每個案例獨立呈現，方便 harness 回傳明確的失敗位置。"""

    def test_01_basic_fields(self):
        """先確認最基本的三個欄位。"""
        self.assertEqual(parse_csv('a,b,c'), ['a', 'b', 'c'])

    def test_02_quoted_comma_in_middle(self):
        """中間欄位的引號內逗號要保留。"""
        self.assertEqual(parse_csv('a,"b,c",d'), ['a', 'b,c', 'd'])

    def test_03_empty_middle_field(self):
        """連續逗號之間是一個空欄位。"""
        self.assertEqual(parse_csv('a,,c'), ['a', '', 'c'])

    def test_04_empty_first_field(self):
        """開頭的逗號代表第一欄為空。"""
        self.assertEqual(parse_csv(',a,b'), ['', 'a', 'b'])

    def test_05_empty_last_field(self):
        """結尾逗號後還有一個空欄位。"""
        self.assertEqual(parse_csv('a,b,'), ['a', 'b', ''])

    def test_06_empty_quoted_field(self):
        """輸入包含兩個雙引號，表示一個空的 quoted field。"""
        self.assertEqual(parse_csv('""'), [''])

    def test_07_escaped_quote(self):
        """連續兩個雙引號應還原成內容中的一個。"""
        self.assertEqual(parse_csv('"a""b",c'), ['a"b', 'c'])

    def test_08_empty_quoted_middle_field(self):
        """空的 quoted field 在中間也要留下。"""
        self.assertEqual(parse_csv('a,"",b'), ['a', '', 'b'])

    def test_09_empty_input(self):
        """輸入長度為零，依題目規格仍回傳一個空欄位。"""
        self.assertEqual(parse_csv(''), [''])

    def test_10_unquoted_spaces(self):
        """一般欄位前後的空白不能自動移除。"""
        self.assertEqual(parse_csv(' a , b '), [' a ', ' b '])
if __name__ == '__main__':
    unittest.main()
