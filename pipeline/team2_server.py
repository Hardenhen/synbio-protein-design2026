#!/usr/bin/env python3
"""Team2 - 独立 GFP 设计（从 amacGFP/cgreGFP/ppluGFP 出发）

3 父代 × 3 温度 × 100 候选 = 900 候选
与 SnowFold (Team1) 完全不同的种子和迭代链
"""
import os, sys, json, time, subprocess, warnings, csv
import torch, numpy as np
warnings.filterwarnings("ignore")
from transformers import AutoTokenizer, EsmForProteinFolding

WORK = "/root/autodl-tmp/team2"
MPNN = "/root/autodl-tmp/ProteinMPNN"
os.makedirs(WORK, exist_ok=True)
for d in ["pdbs", "mpnn_out", "results"]:
    os.makedirs(os.path.join(WORK, d), exist_ok=True)

NUM_SEQ_PER_TEMP = 100
TEMPS = [0.1, 0.2, 0.5]
FIXED = [1, 65, 66, 67, 96, 222]
RECYCLES = 8
BATCH = 25

# 3 个独立 GFP 物种作种子
PARENTS = [
    {"name": "amacGFP", "pdb_id": "7LG4",
     "seq": "MSKGEELFTGIVPVLIELDGDVHGHKFSVRGEGEGDADYGKLEIKFICTTGKLPVPWPTLVTTLSYGILCFARYPEHMKMNDFFKSAMPEGYIQERTIFFQDDGKYKTRGEVKFEGDTLVNRIELKGMDFKEDGNILGHKLEYNFNSHNVYIMPDKANNGLKVNFKIRHNIEGGGVQLADHYQTNVPLGDGPVLIPINHYLSCQTAISKDRNETRDHMVFLEFFSACGHTHGMDELYK"},
    {"name": "cgreGFP", "pdb_id": "2HPW",
     "seq": "MTALTEGAKLFEKEIPYITELEGDVEGMKFIIKGEGTGDATTGTIKAKYICTTGDLPVPWATILSSLSYGVFCFAKYPRHIADFFKSTQPDGYSQDRIISFDNDGQYDVKAKVTYENGTLYNRVTVKGTGFKSNGNILGMRVLYHSPPHAVYILPDRKNGGMKIEYNKAFDVMGGGHQMARHAQFNKPLGAWEEDYPLYHHLTVWTSFGKDPDDDETDHLTIVEVIKAVDLETYR"},
    {"name": "ppluGFP", "pdb_id": "2G6X",
     "seq": "MPAMKIECRITGTLNGVEFELVGGGEGTPEQGRMTNKMKSTKGALTFSPYLLSHVMGYGFYHFGTYPSGYENPFLHAINNGGYTNTRIEKYEDGGVLHVSFSYRYEAGRVIGDFKVVGTGFPEDSVIFTDKIIRSNATVEHLHPMGDNVLVGSFARTFSLRDGGYYSFVVDSHMHFKSAIHPSILQNGGPMFAFRRVEELHSNTELGIVEYQHAFKTPIAFA"},
]

print("Loading ESMFold...", flush=True)
tok = AutoTokenizer.from_pretrained("facebook/esmfold_v1", local_files_only=True)
model = EsmForProteinFolding.from_pretrained("facebook/esmfold_v1", low_cpu_mem_usage=True, local_files_only=True).cuda()
model.trunk.set_chunk_size(128); model.eval()
print("Loaded.", flush=True)

aa3 = {a:b for a,b in zip("ACDEFGHIKLMNPQRSTVWY","ALA CYS ASP GLU PHE GLY HIS ILE LYS LEU MET ASN PRO GLN ARG SER THR VAL TRP TYR".split())}

def predict(seq):
    inputs = tok([seq], return_tensors="pt", add_special_tokens=False)
    inputs = {k:v.cuda() for k,v in inputs.items()}
    with torch.no_grad():
        out = model(**inputs, num_recycles=RECYCLES)
    plddt = out.plddt[0,:,1].cpu().numpy()
    ptm = float(out.ptm.cpu().item())
    gp = float(plddt.mean()); cp = float(plddt[57:72].mean())
    score = 0.40*ptm + 0.30*gp + 0.30*cp
    return {"ptm":round(ptm,4),"plddt":round(gp,4),"chromo":round(cp,4),"score":round(score,4),"passes":ptm>0.6 and gp>0.6 and cp>0.55}

def save_pdb(seq, path):
    inputs = tok([seq], return_tensors="pt", add_special_tokens=False)
    inputs = {k:v.cuda() for k,v in inputs.items()}
    with torch.no_grad():
        out = model(**inputs, num_recycles=RECYCLES)
    plddt = out.plddt[0,:,1].cpu().numpy()
    pos = out.positions[-1][0].cpu().numpy()
    with open(path,"w") as f:
        f.write("REMARK Team2\n"); aidx=1
        for i,a in enumerate(seq):
            rn=aa3.get(a,"ALA")
            for j,an in enumerate(["N","CA","C","O"]):
                x,y,z=pos[i,j]
                f.write(f"ATOM  {aidx:5d} {an:^4s} {rn:3s} A{i+1:4d}    {x:8.3f}{y:8.3f}{z:8.3f}{1.0:6.2f}{plddt[i]*100:6.2f}\n")
                aidx+=1
        f.write("END\n")

def list_fa(outdir):
    seqs_dir=os.path.join(outdir,"seqs"); res=[]
    if not os.path.isdir(seqs_dir): return []
    for root,dirs,files in os.walk(seqs_dir):
        for f in files:
            if f.endswith(".fa"): res.append(os.path.join(root,f))
    return sorted(res)

def parse_fa(paths):
    out=[]
    for p in paths:
        n=""; s=""
        with open(p,encoding="utf-8",errors="replace") as f:
            for line in f:
                line=line.strip()
                if line.startswith(">"):
                    if s: out.append({"name":n,"seq":s})
                    n=line[1:]; s=""
                elif line: s+=line
            if s: out.append({"name":n,"seq":s})
    return out

def run_mpnn(pdb, name):
    outdir = os.path.join(WORK, "mpnn_out", name)
    os.makedirs(outdir, exist_ok=True)
    fixed_json = os.path.join(outdir, "fixed.jsonl")
    key = os.path.basename(pdb).replace(".pdb","")
    with open(fixed_json,"w") as f:
        f.write(json.dumps({key:{"A":FIXED}})+"\n")
    cmd = [sys.executable, os.path.join(MPNN,"protein_mpnn_run.py"),
           "--pdb_path", pdb, "--pdb_path_chains", "A",
           "--path_to_model_weights", os.path.join(MPNN,"vanilla_model_weights"),
           "--fixed_positions_jsonl", fixed_json, "--out_folder", outdir,
           "--num_seq_per_target", str(NUM_SEQ_PER_TEMP), "--batch_size", str(BATCH),
           "--sampling_temp", " ".join(map(str,TEMPS)),
           "--seed", "42", "--suppress_print", "1"]
    print(f"  [MPNN] {name}...", end="", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    files = list_fa(outdir)
    print(f" {len(files)} files", flush=True)
    if not files:
        print(f"  STDERR: {r.stderr[-300:]}", flush=True)
    return files

if __name__ == "__main__":
    t0 = time.time()
    print(f"Team2 Start: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"Parents: {[p['name'] for p in PARENTS]}", flush=True)
    print(f"Temps: {TEMPS}, Fixed: {FIXED}", flush=True)

    all_passed = []
    for i, parent in enumerate(PARENTS):
        pn = f"t2_{parent['name']}"
        ps = parent["seq"]
        print(f"\n[Parent {i+1}/3] {parent['name']} ({len(ps)}aa, PDB: {parent['pdb_id']})", flush=True)

        # ESMFold -> PDB
        pdb = os.path.join(WORK, "pdbs", f"{pn}.pdb")
        if not os.path.isfile(pdb):
            print(f"  ESMFold r=8 -> PDB...", end="", flush=True)
            save_pdb(ps, pdb)
            print(" done", flush=True)

        # MPNN
        files = run_mpnn(pdb, pn)
        if not files:
            print(f"  MPNN failed for {pn}", flush=True)
            continue

        # Parse + screen
        seqs = parse_fa(files)
        filt = [x for x in seqs if x["seq"] != ps and x["seq"].startswith("M") and 220 <= len(x["seq"]) <= 250]
        print(f"  filtered: {len(filt)}", flush=True)
        if not filt:
            continue

        passed = []
        print(f"  [screen] {len(filt)} candidates @ r={RECYCLES}", flush=True)
        for j, e in enumerate(filt):
            s = e["seq"]
            try: m = predict(s)
            except Exception:
                torch.cuda.empty_cache(); continue
            if not m["passes"]: continue
            m["seq"]=s; m["name"]=e["name"][:50]; m["parent"]=parent["name"]
            m["length"]=len(s); m["recycles"]=RECYCLES
            passed.append(m); all_passed.append(m)
            torch.cuda.empty_cache()
            if (j+1)%50==0:
                print(f"    [{time.strftime('%H:%M:%S')}] {j+1}/{len(filt)}, {len(passed)} passed", flush=True)
        passed.sort(key=lambda x:x["score"], reverse=True)
        print(f"  {parent['name']}: {len(passed)}/{len(filt)} passed, top={passed[0]['score']:.4f}" if passed else f"  {parent['name']}: 0 passed", flush=True)
        json.dump(all_passed, open(os.path.join(WORK,"results","progress.json"),"w"), indent=2)

    # Final
    all_passed.sort(key=lambda x:x["score"], reverse=True)
    json.dump(all_passed, open(os.path.join(WORK,"all_passed.json"),"w"), indent=2)
    print(f"\nTotal passed: {len(all_passed)}", flush=True)
    print(f"Top 15:", flush=True)
    for i, c in enumerate(all_passed[:15]):
        print(f"  {i+1:2d}. parent={c['parent']:10s} score={c['score']:.4f} pTM={c['ptm']:.4f} chromo={c['chromo']:.3f}", flush=True)

    final6 = all_passed[:6]
    json.dump(final6, open(os.path.join(WORK,"final_6.json"),"w"), indent=2)
    with open(os.path.join(WORK,"submission.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["Team_Name","Seq_ID","Sequence"])
        for i,c in enumerate(final6): w.writerow(["BioForge",i+1,c["seq"]])
    print(f"\nDone: {time.strftime('%Y-%m-%d %H:%M:%S')} ({(time.time()-t0)/60:.1f} min)", flush=True)
