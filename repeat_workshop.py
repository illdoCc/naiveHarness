"""課前依指定 seed 重跑，保存每輪 Notebook 與分數，學生不必閱讀這支程式。"""

import argparse
import copy
import json
import re
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

from verify_workshop import check_cases, check_loop, check_runner

ROOT = Path(__file__).resolve().parent


def main():
    """固定題目與模型參數，依序使用指定 seed；重複 seed 也會分開存檔。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', nargs='+', type=int, default=[7, 17, 27])
    parser.add_argument('--demo', action='store_true', help='只檢查重跑流程，不呼叫模型')
    args = parser.parse_args()
    template = nbformat.read(ROOT / 'workshop.ipynb', as_version=4)
    nbformat.validate(template)
    check_cases(template)
    check_runner()
    check_loop(template)
    mode = 'demo' if args.demo else 'ollama'
    folder = ROOT / 'runs' / f'csv-repeat-{mode}-{time.time_ns()}'
    folder.mkdir(parents=True)
    nbformat.write(template, folder / 'template.ipynb')
    report = {'mode': mode, 'seeds': args.seeds, 'status': 'running', 'runs': []}
    main_saved = False

    def save_report():
        """每輪更新總表；失敗的輪次也保留，不挑選漂亮的結果。"""
        (folder / 'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    print('輸出目錄：', folder, flush=True)
    for round_number, seed in enumerate(args.seeds, 1):
        notebook = copy.deepcopy(template)
        for cell in notebook.cells:
            if cell.cell_type == 'code':
                cell.outputs = []
                cell.execution_count = None
                cell.metadata.pop('execution', None)
            if cell.id == 'setup':
                cell.source = cell.source.replace('MODE = "ollama"', f'MODE = "{mode}"')
                cell.source, matches = re.subn(r'"seed":\s*\d+', f'"seed": {seed}', cell.source)
                assert matches == 1
        checkpoint = folder / f'round-{round_number}-seed-{seed}-partial.ipynb'
        row = {'round': round_number, 'seed': seed, 'status': 'running'}
        report['runs'].append(row)
        save_report()
        print(f'\n開始第 {round_number} 輪，seed={seed}，模式={mode}', flush=True)

        def on_cell_start(cell, **kwargs):
            """推論前印出目前階段，方便確認長時間執行的進度。"""
            if cell.id == 'baseline':
                print('正在生成共同起點……', flush=True)
            elif cell.id == 'run-repair':
                print('正在依序比較 Retry Only、Raw……', flush=True)

        def on_cell_executed(cell, **kwargs):
            """每格完成就備存，並回報模型分數與最後表格。"""
            nbformat.write(notebook, checkpoint)
            if cell.id in {'baseline', 'run-repair', 'comparison'}:
                for output in cell.get('outputs', []):
                    if output.output_type == 'stream':
                        print(output.text, end='', flush=True)
                    elif 'text/markdown' in output.get('data', {}):
                        print(output.data['text/markdown'], flush=True)

        started = time.perf_counter()
        try:
            NotebookClient(notebook, timeout=1900, kernel_name='python3',
                           resources={'metadata': {'path': str(ROOT)}},
                           on_cell_start=on_cell_start,
                           on_cell_executed=on_cell_executed).execute()
            comparison = next(cell for cell in notebook.cells if cell.id == 'comparison')
            trace_names = [line.split('紀錄已保存：', 1)[1].strip()
                           for output in comparison.outputs if output.output_type == 'stream'
                           for line in output.text.splitlines() if '紀錄已保存：' in line]
            assert len(trace_names) == 1
            trace = json.loads((ROOT / trace_names[0]).read_text(encoding='utf-8'))
            assert trace['options']['seed'] == seed and trace['mode'] == mode
            assert len(trace['development_cases']) == 10 and 'acceptance_cases' not in trace
            assert set(trace['experiments']) == {'retry', 'raw'}
            row.update(status='complete', seconds=time.perf_counter() - started,
                       trace=trace_names[0], scores={item['group']: item['development']['count']
                                                   for item in trace['summary']},
                       summary=trace['summary'])
            destination = folder / f'round-{round_number}-seed-{seed}.ipynb'
            nbformat.write(notebook, destination)
            row['notebook'] = str(destination)
            if not args.demo and not main_saved:
                nbformat.write(notebook, ROOT / 'workshop.ipynb')
                main_saved = True
                report['main_notebook_seed'] = seed
            print(f"seed={seed} 完成，耗時 {row['seconds']:.1f} 秒。", flush=True)
        except Exception as error:
            nbformat.write(notebook, checkpoint)
            row.update(status='error', seconds=time.perf_counter() - started, error=repr(error))
            print(f'seed={seed} 未完成：{error}', flush=True)
        finally:
            save_report()
    report['status'] = 'complete' if all(row['status'] == 'complete' for row in report['runs']) else 'partial'
    save_report()
    print('\n重跑紀錄：', folder / 'summary.json', flush=True)
    for row in report['runs']:
        print(row['round'], row['seed'], row['status'], row.get('scores', {}), flush=True)
    if report['status'] != 'complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
