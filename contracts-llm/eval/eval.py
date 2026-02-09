# eval/eval.py
# Minimal skeleton to evaluate HasCitation & simple accuracy if JSON field 'verdict' exists.
import json, sys, pathlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'datasets'

def main():
    gold = []
    pred = []
    # Expect two files for quick test: gold.jsonl and pred.jsonl (same order)
    g = DATA/'gold.jsonl'
    p = DATA/'pred.jsonl'
    if not g.exists() or not p.exists():
        print('[eval] Put gold.jsonl and pred.jsonl in eval/datasets/')
        return
    with g.open('r', encoding='utf-8') as f:
        gold = [json.loads(l) for l in f]
    with p.open('r', encoding='utf-8') as f:
        pred = [json.loads(l) for l in f]

    n = min(len(gold), len(pred))
    ok = 0; cited = 0
    for i in range(n):
        gv = gold[i].get('answer',{}).get('verdict')
        pv = pred[i].get('answer',{}).get('verdict')
        if gv and pv and gv.strip().lower()==pv.strip().lower():
            ok += 1
        # count citation presence
        cites = pred[i].get('answer',{}).get('citations',[])
        if cites: cited += 1

    print(f'[eval] N={n}  VerdictAccuracy={ok/n if n else 0:.3f}  HasCitation={cited/n if n else 0:.3f}')

if __name__ == '__main__':
    main()
