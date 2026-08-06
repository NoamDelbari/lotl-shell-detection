"""Extract usable shell command lines from downloaded commandlinefu JSON pages."""
import json, glob, re, os, random, html

BASE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(BASE, "pages")
NL2BASH = "E:/ai_malware_and_intrusion/final_project/scripts/raw/nl2bash.cm"

def collapse(s):
    return re.sub(r"\s+", " ", s).strip()

raw_items = []
seen_ids = set()
for fp in sorted(glob.glob(os.path.join(PAGES, "page_*.json"))):
    with open(fp, encoding="utf-8") as f:
        try:
            items = json.load(f)
        except Exception as e:
            print(f"BAD JSON {fp}: {e}")
            continue
    for it in items:
        cid = it.get("id")
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        raw_items.append(it)

print(f"raw items (unique ids): {len(raw_items)}")

kb_shortcut = re.compile(r"(?i)^\W*(ctrl|alt|esc|meta|shift|cmd)[\-\+ ]")
ps_verb = re.compile(r"^(Get|Set|New|Remove|Invoke|Start|Stop|Add|Out|Write|Test)-[A-Z]")
dropped = {"empty": 0, "kbshortcut": 0, "powershell": 0, "noalpha": 0, "natlang": 0}

usable = {}   # collapsed -> original (first seen)
for it in raw_items:
    cmd = it.get("command") or ""
    cmd = html.unescape(cmd)
    # strip leading shell prompt markers
    cmd = re.sub(r"^\s*\$\s+", "", cmd)
    c = collapse(cmd)
    if not c or len(c) < 2:
        dropped["empty"] += 1
        continue
    if kb_shortcut.match(c) and len(c) < 40:
        dropped["kbshortcut"] += 1
        continue
    if ps_verb.match(c):
        dropped["powershell"] += 1
        continue
    if not re.search(r"[A-Za-z]", c):
        dropped["noalpha"] += 1
        continue
    # crude natural-language filter: many words, no shell metachar, ends with period,
    # and first word capitalized -> likely a description not a command
    words = c.split()
    if (len(words) >= 6 and not re.search(r"[|;&<>$/=\-'\"`(){}\[\]~*]", c)
            and c[0].isupper()):
        dropped["natlang"] += 1
        continue
    if c not in usable:
        usable[c] = cmd

print(f"dropped: {dropped}")
print(f"distinct usable commands (case-kept, ws-collapsed): {len(usable)}")

out = os.path.join(BASE, "commandlinefu_commands.txt")
with open(out, "w", encoding="utf-8") as f:
    for c in usable:
        f.write(c + "\n")
print(f"wrote {out}")

# ---- overlap with nl2bash ----
def norm_lc(s):
    return re.sub(r"\s+", " ", s).strip().lower()

nl2 = set()
nl2_case = set()
with open(NL2BASH, encoding="utf-8", errors="replace") as f:
    for line in f:
        nl2.add(norm_lc(line))
        nl2_case.add(collapse(line))

pool = list(usable.keys())
random.seed(42)
sample = random.sample(pool, min(500, len(pool)))
hits_lc = sum(1 for c in sample if norm_lc(c) in nl2)
hits_case = sum(1 for c in sample if c in nl2_case)
print(f"overlap sample n={len(sample)}")
print(f"  lowercase+ws-collapse exact hits: {hits_lc} ({100*hits_lc/len(sample):.1f}%)")
print(f"  case-kept+ws-collapse exact hits: {hits_case} ({100*hits_case/len(sample):.1f}%)")

# whole-pool overlap too (cheap)
all_hits = sum(1 for c in pool if norm_lc(c) in nl2)
print(f"whole-pool lowercase overlap: {all_hits}/{len(pool)} ({100*all_hits/len(pool):.2f}%)")

print("\n5 examples:")
for c in random.sample(pool, 5):
    print("  ", c[:200])
