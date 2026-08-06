import json, re, random, collections, sys

SRC = r"C:/Users/noham/AppData/Local/Temp/claude/E--ai-malware-and-intrusion/f054ff10-cc94-490f-951e-3a5f1e9cdb27/scratchpad/candidates/1_Frost2o24_bash-instruct-55k/bash_dataset.jsonl"
NL2BASH = r"E:/ai_malware_and_intrusion/final_project/scripts/raw/nl2bash.cm"
OUT = r"C:/Users/noham/AppData/Local/Temp/claude/E--ai-malware-and-intrusion/f054ff10-cc94-490f-951e-3a5f1e9cdb27/scratchpad/candidates/1_Frost2o24_bash-instruct-55k/extracted_commands.txt"

ws = re.compile(r"\s+")

def norm(s):
    return ws.sub(" ", s.strip())

n_rows = 0
n_bad_json = 0
n_no_assistant = 0
n_multiline = 0
n_empty = 0
n_dropped_nonshell = 0
cats = collections.Counter()
utils = collections.Counter()
commands = []

# heuristics: drop lines that look like natural language (no shell token and >6 words
# with no typical command start), powershell, markdown fences
ps_pat = re.compile(r"^(Get-|Set-|New-|Remove-|Invoke-|powershell|cmd\.exe|cmd /c)", re.I)

with open(SRC, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        n_rows += 1
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            n_bad_json += 1
            continue
        msgs = rec.get("messages", [])
        if not msgs or msgs[-1].get("role") != "assistant":
            n_no_assistant += 1
            continue
        cmd = msgs[-1].get("content", "")
        cats[rec.get("category", "?")] += 1
        utils[rec.get("utility", "?")] += 1
        if "\n" in cmd.strip():
            n_multiline += 1
            # keep only if it's a short multi-line that joins cleanly? no - drop, count them
            continue
        c = norm(cmd)
        if not c:
            n_empty += 1
            continue
        # strip markdown fences if present
        c = re.sub(r"^```(?:bash|sh)?\s*|\s*```$", "", c).strip()
        if not c:
            n_empty += 1
            continue
        if ps_pat.match(c):
            n_dropped_nonshell += 1
            continue
        commands.append(c)

distinct = sorted(set(commands))
print(f"rows={n_rows} bad_json={n_bad_json} no_assistant={n_no_assistant} multiline_dropped={n_multiline} empty={n_empty} nonshell={n_dropped_nonshell}")
print(f"extracted_total={len(commands)} distinct={len(distinct)}")
print("categories:", dict(cats.most_common()))
print("top utilities:", utils.most_common(25))
print("n_distinct_utilities:", len(utils))

with open(OUT, "w", encoding="utf-8") as f:
    for c in distinct:
        f.write(c + "\n")

# length stats
lens = sorted(len(c) for c in distinct)
import statistics
print(f"len: min={lens[0]} med={lens[len(lens)//2]} p90={lens[int(len(lens)*0.9)]} max={lens[-1]}")

# overlap with nl2bash
pool = set()
with open(NL2BASH, encoding="utf-8", errors="replace") as f:
    for line in f:
        pool.add(norm(line))
print(f"nl2bash pool size (distinct, ws-collapsed): {len(pool)}")

random.seed(42)
sample = random.sample(distinct, min(500, len(distinct)))
hits = [c for c in sample if c in pool]
print(f"overlap sample={len(sample)} exact_hits={len(hits)} pct={100.0*len(hits)/len(sample):.2f}")
for h in hits[:10]:
    print("  HIT:", h)

# case-insensitive check as extra info
pool_lc = {p.lower() for p in pool}
hits_lc = [c for c in sample if c.lower() in pool_lc]
print(f"overlap (lowercased) hits={len(hits_lc)} pct={100.0*len(hits_lc)/len(sample):.2f}")

# examples
print("\nEXAMPLES:")
for c in random.sample(distinct, 12):
    print("  ", c)
