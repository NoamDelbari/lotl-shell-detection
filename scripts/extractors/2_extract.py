import pandas as pd
import re, random

BASE = "C:/Users/noham/AppData/Local/Temp/claude/E--ai-malware-and-intrusion/f054ff10-cc94-490f-951e-3a5f1e9cdb27/scratchpad/candidates/2_emirkaanozdemr_bash_command_data_6K"
df = pd.read_parquet(f"{BASE}/train.parquet")

def norm(s): return re.sub(r"\s+", " ", s).strip()

raw = df["completion"].astype(str).tolist()

usable = set()
n_single = n_multi_salvaged = n_script_skipped = n_dollar_stripped = 0

for c in raw:
    body = c.strip()
    if not body:
        continue
    lines = body.split("\n")
    if len(lines) == 1:
        n = norm(lines[0])
        if n.startswith("$ "):
            n = n[2:].strip()
            n_dollar_stripped += 1
        if n and not n.startswith("#"):
            usable.add(n)
            n_single += 1
    else:
        if lines[0].strip().startswith("#!"):
            n_script_skipped += 1
            continue
        # command + output demo block: take the first line only (the command);
        # subsequent lines are example output (commented or raw)
        first = norm(lines[0])
        if first.startswith("$ "):
            first = first[2:].strip()
        if first and not first.startswith("#"):
            usable.add(first)
            n_multi_salvaged += 1
        # also salvage additional '$ '-prefixed command lines within the block
        for ln in lines[1:]:
            n = norm(ln)
            if n.startswith("$ "):
                cmd = n[2:].strip()
                if cmd and not cmd.startswith("#"):
                    usable.add(cmd)

print("single-line kept:", n_single)
print("multiline first-line salvaged:", n_multi_salvaged)
print("shebang scripts skipped:", n_script_skipped)
print("dollar-prefix stripped (single-line):", n_dollar_stripped)

distinct = sorted(usable)
print("FINAL DISTINCT USABLE:", len(distinct))

# sanity: junk-looking survivors (pure numbers / output-looking)
junk = [d for d in distinct if re.fullmatch(r"[\d .:%-]+", d)]
print("junk-looking (pure numeric):", len(junk), junk[:5])

# overlap with nl2bash on 500-sample
with open("E:/ai_malware_and_intrusion/final_project/scripts/raw/nl2bash.cm", encoding="utf-8", errors="replace") as f:
    nl2 = set(norm(l) for l in f if l.strip())
random.seed(42)
sample = random.sample(distinct, min(500, len(distinct)))
hits = sum(1 for s in sample if s in nl2)
print(f"sample overlap with nl2bash: {hits}/{len(sample)} = {100*hits/len(sample):.1f}%")
full_hits = sum(1 for s in distinct if s in nl2)
print(f"full overlap: {full_hits}/{len(distinct)} = {100*full_hits/len(distinct):.2f}%")

with open(f"{BASE}/extracted_commands.txt", "w", encoding="utf-8") as f:
    for d in distinct:
        f.write(d + "\n")

print("\n5 random examples:")
for e in random.sample(distinct, 5):
    print("EX:", e[:180])
