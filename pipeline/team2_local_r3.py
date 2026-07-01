#!/usr/bin/env python3
"""Team2 local round3 ultra-low/mid refinement (~135 candidates)

Use local R2 Top3 as parents, push from 0.9291 toward 0.94.
"""
import os, sys, json, time, subprocess, warnings, csv
import torch
warnings.filterwarnings("ignore")
from transformers import AutoTokenizer, EsmForProteinFolding

WORK = "D:/workspace/team2_local_r3"
MPNN_DIR = "C:/proteinmpnn_r10"
os.makedirs(WORK, exist_ok=True)
for d in ["pdbs","mpnn_out","results"]:
    os.makedirs(os.path.join(WORK,d), exist_ok=True)

PARENTS = json.load(open(r"D:/workspace/team2_local_r2/final_6_local_r2.json"))[:3]
TEMPS = [0.02, 0.05, 0.1]
NUM_SEQ_PER_TEMP = 15
FIXED = [1,65,66,67,96,222]
RECYCLES = 8
BATCH = 4

aa3 = {a:b for a,b in zip("ACDEFGHIKLMNPQRSTVWY","ALA CYS ASP GLU PHE GLY HIS ILE LYS LEU MET ASN PRO GLN ARG SER THR VAL TRP TYR".split())}

print("Loading ESMFold local chunk=64...", flush=True)
tok = AutoTokenizer.from_pretrained("facebook/esmfold_v1", local_files_only=True)
model = EsmForProteinFolding.from_pretrained("facebook/esmfold_v1", low_cpu_mem_usage=True, local_files_only=True).cuda()
model.trunk.set_chunk_size(64); model.eval()
print("Loaded.", flush=True)

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
        f.write("REMARK TEAM2_LOCAL_R3\n"); aidx=1
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
    outdir=os.path.join(WORK,"mpnn_out",name)
    os.makedirs(outdir, exist_ok=True)
    fixed=os.path.join(outdir,"fixed.jsonl")
    key=os.path.basename(pdb).replace(".pdb","")
    with open(fixed,"w") as f:
        f.write(json.dumps({key:{"A":FIXED}})+"\n")
    cmd=[sys.executable, os.path.join(MPNN_DIR,"protein_mpnn_run.py"),
         "--pdb_path", pdb.replace('\\','/'), "--pdb_path_chains", "A",
         "--path_to_model_weights", os.path.join(MPNN_DIR,"vanilla_model_weights"),
         "--fixed_positions_jsonl", fixed, "--out_folder", outdir,
         "--num_seq_per_target", str(NUM_SEQ_PER_TEMP), "--batch_size", str(BATCH),
         "--sampling_temp", " ".join(map(str,TEMPS)), "--seed", "2804", "--suppress_print", "1"]
    print(f"  [MPNN] {name} temps={TEMPS}...", end="", flush=True)
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=900)
    files=list_fa(outdir)
    print(f" {len(files)} files", flush=True)
    return files

if __name__ == "__main__":
    t0=time.time()
    print(f"Team2 Local R3 Start: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"Parents: {[p.get('score') for p in PARENTS]}", flush=True)
    all_passed=[]
    for i,p in enumerate(PARENTS):
        pn=f"r3_p{i+1}"
        pdb=os.path.join(WORK,"pdbs",f"{pn}.pdb")
        if not os.path.isfile(pdb):
            print(f"[Parent {i+1}/{len(PARENTS)}] PDB...", end="", flush=True)
            save_pdb(p["seq"], pdb)
            print(" done", flush=True)
        files=run_mpnn(pdb,pn)
        seqs=parse_fa(files)
        filt=[x for x in seqs if x["seq"]!=p["seq"] and x["seq"].startswith("M")]
        print(f"  filtered={len(filt)}", flush=True)
        passed=[]
        for j,e in enumerate(filt):
            m=predict(e["seq"])
            if m["passes"]:
                m.update({"seq":e["seq"],"name":e["name"][:50],"parent":pn,"length":len(e["seq"]),"recycles":RECYCLES})
                passed.append(m); all_passed.append(m)
            torch.cuda.empty_cache()
            if (j+1)%25==0:
                print(f"    [{time.strftime('%H:%M:%S')}] {j+1}/{len(filt)}, {len(passed)} passed", flush=True)
        print(f"  {pn}: {len(passed)}/{len(filt)} passed, top={max([x['score'] for x in passed], default=0):.4f}", flush=True)
    all_passed.sort(key=lambda x:x["score"], reverse=True)
    json.dump(all_passed, open(os.path.join(WORK,"all_passed_local_r3.json"),"w"), indent=2)
    final6=all_passed[:6]
    json.dump(final6, open(os.path.join(WORK,"final_6_local_r3.json"),"w"), indent=2)
    with open(os.path.join(WORK,"submission_local_r3.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["Team_Name","Seq_ID","Sequence"])
        for i,c in enumerate(final6): w.writerow(["ＡＵＲＯＲＡ",i+1,c["seq"]])
    print("\nTop 10:", flush=True)
    for i,c in enumerate(all_passed[:10]):
        print(f"  {i+1}. score={c['score']:.4f} pTM={c['ptm']:.4f} chromo={c['chromo']:.3f} parent={c['parent']}", flush=True)
    print(f"Done: {(time.time()-t0)/60:.1f} min", flush=True)
