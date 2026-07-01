import csv, json, os, itertools
AA='ACDEFGHIKLMNPQRSTVWY'
submission = r'D:\workspace\ＡＵＲＯＲＡ-GFP-2026\submission\submission_team2.csv'
final_json = r'D:\workspace\ＡＵＲＯＲＡ-GFP-2026\results\local_r2\final_6_local_r2.json'
team1_json = r'D:\workspace\round25\final_6_r25.json'
excl_path = r'D:\生信\2026Protein Design\Exclusion_List.csv'

def load_excl(path):
    s=set()
    if os.path.exists(path):
        with open(path,encoding='utf-8') as f:
            for line in f:
                for p in line.strip().split(','):
                    p=p.strip().upper()
                    if len(p)>50 and all(c in AA for c in p): s.add(p)
    return s

def ident(a,b):
    L=min(len(a),len(b))
    return sum(x==y for x,y in zip(a[:L],b[:L]))/max(L,1)

excl=load_excl(excl_path)
rows=list(csv.DictReader(open(submission,encoding='utf-8')))
final=json.load(open(final_json,encoding='utf-8'))
team1=json.load(open(team1_json,encoding='utf-8')) if os.path.exists(team1_json) else []
team1_seqs=[c.get('seq',c.get('sequence','')) for c in team1]
print('Exclusion list:', len(excl))
print('Rows:', len(rows))
print('Header:', list(rows[0].keys()) if rows else None)
all_ok=True
for i,r in enumerate(rows):
    seq=r['Sequence'].strip()
    m=seq.startswith('M')
    l=220<=len(seq)<=250
    aa=all(c in AA for c in seq)
    ex=seq not in excl
    uq=rows.count(r)==1
    max_team1=max([ident(seq,s) for s in team1_seqs], default=0)
    max_self=max([ident(seq, rows[j]['Sequence'].strip()) for j in range(len(rows)) if j!=i], default=0)
    score=final[i].get('score') if i < len(final) else None
    ok=m and l and aa and ex and max_team1<0.85 and max_self<0.98
    all_ok=all_ok and ok
    print(f"Seq{i+1}: len={len(seq)} M={m} AA={aa} exclusion={ex} score={score:.4f} max_vs_Team1={max_team1:.1%} max_self={max_self:.1%} PASS={ok}")
print('OVERALL:', 'PASS' if all_ok else 'FAIL')
