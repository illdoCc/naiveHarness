"""把模型連線、固定案例和測試執行放在這裡，Notebook 專心看回饋與迴圈。"""

import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

DEV_CASES = [('a,b,c', ['a', 'b', 'c']),
 ('a,"b,c",d', ['a', 'b,c', 'd']),
 ('a,,c', ['a', '', 'c']),
 (',a,b', ['', 'a', 'b']),
 ('a,b,', ['a', 'b', '']),
 ('""', ['']),
 ('"a""b",c', ['a"b', 'c']),
 ('a,"",b', ['a', '', 'b']),
 ('', ['']),
 (' a , b ', [' a ', ' b '])]

# 手寫正解只給示例模式與課前檢查使用，不會送給真實模型。
DEMO_CODE = '''def parse_csv(line: str) -> list[str]:
    """逐字解析，遇到引號內的雙引號配對就保留一個。"""
    result, field = [], []
    in_quotes = False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"':
            if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                field.append('"')
                i += 1
            else:
                in_quotes = not in_quotes
        elif ch == ',' and not in_quotes:
            result.append(''.join(field))
            field = []
        else:
            field.append(ch)
        i += 1
    result.append(''.join(field))
    return result
'''



def extract_code(reply):
    """模型有時會加上程式碼框，所以先取出裡面的 Python。"""
    match = re.search(r"```(?:python|py)?\s*\n(.*?)```", reply, re.DOTALL)
    return (match.group(1) if match else reply).strip() + "\n"


def write_solution(root, filename, code):
    """這個工具只開放解答檔，因此不能拿它改測試或其他路徑。"""
    if filename != "solution.py":
        raise PermissionError("只能修改 solution.py，測試與其他檔案不開放。")
    path = Path(root) / filename
    path.write_text(code, encoding="utf-8")
    return path


def ask_ollama(messages, model, options, think=False):
    """把對話交給本地 Ollama，遇到連線失敗或輸出截斷就明確報錯。"""
    payload = {"model": model, "messages": messages, "stream": False,
               "think": think, "options": options}
    request = Request("http://localhost:11434/api/chat",
                      data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=600) as response:
            data = json.load(response)
    except (URLError, TimeoutError) as error:
        raise RuntimeError("請確認 Ollama 已啟動、模型已下載；CPU 較慢時可調高 timeout。") from error
    if data.get("done_reason") == "length":
        raise RuntimeError("模型輸出被截斷了，請調高 OPTIONS 的 num_predict 後重跑。")
    return data["message"]["content"]


# 同一次 unittest 執行，同時留下原始輸出與每個失敗案例，避免兩種回饋各測各的。
RUNNER = r'''
import io
import json
import runpy
import sys
import unittest

parse_csv = runpy.run_path("solution.py")["parse_csv"]
rows = []
checker = unittest.TestCase()
checker.maxDiff = None

def make_test(index, line, expected):
    """把固定案例包成 unittest，並保留可供分類的原始結果。"""
    def check():
        """執行這一筆案例；失敗時仍讓 unittest 產生正常的錯誤輸出。"""
        row = {"case": index, "passed": False,
               "detail": f"test_{index:02d}\nInput: {line!r}\nExpected: {expected!r}"}
        try:
            actual = parse_csv(line)
            row["actual"] = repr(actual)
            row["detail"] += f"\nActual: {actual!r}"
            checker.assertIsInstance(actual, list)
            checker.assertEqual(actual, expected)
            row["passed"] = True
        except Exception as error:
            if "actual" not in row:
                row["detail"] += f"\nException: {type(error).__name__}: {error}"
            raise
        finally:
            rows.append(row)
    return unittest.FunctionTestCase(
        check, description=f"test_{index:02d} Input: {line!r}\nExpected: {expected!r}")

cases = json.load(sys.stdin)
suite = unittest.TestSuite(make_test(i, line, expected)
                           for i, (line, expected) in enumerate(cases, 1))
output = io.StringIO()
unittest.TextTestRunner(stream=output, verbosity=1).run(suite)
print(json.dumps({"rows": rows, "raw": output.getvalue()}, ensure_ascii=False))
'''


def failed_result(message, total):
    """測試還沒跑起來時，也把語法錯誤或逾時整理成失敗結果。"""
    return {"passed": False, "count": 0, "total": total,
            "feedback": message, "raw": message, "failures": []}


def run_tests(code, cases, timeout=3):
    """在新暫存程序跑 unittest；保留原始與結構化結果，但不替模型修程式。"""
    if not cases:
        raise ValueError("至少要有一個測試，不能把零個測試算成成功。")
    try:
        tree = ast.parse(code)
    except SyntaxError:
        tree = ast.Module(body=[], type_ignores=[])
    for node in ast.walk(tree):
        names = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                 else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
        if any(name.split('.')[0] in {"csv", "_csv"} for name in names):
            return failed_result("題目禁止使用 csv／_csv library，請自行解析欄位。", len(cases))
    with tempfile.TemporaryDirectory(prefix="harness-") as folder:
        write_solution(folder, "solution.py", code)
        try:
            process = subprocess.run(
                [sys.executable, "-I", "-c", RUNNER], cwd=folder,
                input=json.dumps(cases), capture_output=True, text=True,
                encoding="utf-8", timeout=timeout)
        except subprocess.TimeoutExpired:
            return failed_result(f"執行超過 {timeout} 秒，請檢查是否有無限迴圈。", len(cases))
    if process.returncode != 0:
        return failed_result((process.stderr or process.stdout)[-2000:], len(cases))
    try:
        data = json.loads(process.stdout)
    except json.JSONDecodeError:
        return failed_result("請定義 parse_csv，不要在函式外印出內容。", len(cases))
    # 舊的獨立試題程式仍可替換 RUNNER；CSV 路徑則使用真正的 unittest 輸出。
    rows = data if isinstance(data, list) else data["rows"]
    count = sum(row["passed"] for row in rows)
    failures = [row for row in rows if not row["passed"]]
    feedback = f"{count}/{len(cases)} 個測試通過。\n" + "\n".join(row["detail"] for row in failures)
    return {"passed": count == len(cases), "count": count, "total": len(cases),
            "feedback": feedback, "raw": feedback if isinstance(data, list) else data["raw"],
            "failures": failures}
