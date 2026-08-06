import pandas as pd, re, random, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"C:/Users/noham/AppData/Local/Temp/claude/E--ai-malware-and-intrusion/f054ff10-cc94-490f-951e-3a5f1e9cdb27/scratchpad/candidates/3_missvector_linux-commands"

def load(prefix):
    dfs = []
    for split in ["train", "validation", "test"]:
        df = pd.read_parquet(f"{BASE}/{prefix}_{split}.parquet")
        df["split"] = split
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

eng = load("eng")
default = load("data")

print("ENG columns:", list(eng.columns), "rows:", len(eng))
print("DEFAULT columns:", list(default.columns), "rows:", len(default))
print("\nENG sample rows:")
print(eng.head(5).to_string())
print("\nDEFAULT sample rows:")
print(default.head(3).to_string())

def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip()

# figure out the command column
cmd_col = None
for c in ["completion", "command", "cmd", "output"]:
    if c in eng.columns:
        cmd_col = c
        break
print("\nUsing command column:", cmd_col)

def usable(cmd):
    if not cmd or len(cmd) < 2:
        return False
    # drop obvious natural language (no command-like start)
    # drop powershell/cmd markers
    low = cmd.lower()
    if low.startswith(("powershell", "cmd.exe", "cmd /c", "reg add", "certutil", "wmic")):
        return False
    # drop lines that are pure placeholders
    if re.fullmatch(r"[<>\[\]{}. ]+", cmd):
        return False
    return True

eng_cmds = [norm(c) for c in eng[cmd_col].tolist()]
eng_usable = sorted({c for c in eng_cmds if usable(c)})
print("\nENG total rows:", len(eng_cmds), "-> distinct usable:", len(eng_usable))

def_cmds = [norm(c) for c in default[cmd_col].tolist()] if cmd_col in default.columns else []
def_usable = sorted({c for c in def_cmds if usable(c)})
print("DEFAULT total rows:", len(def_cmds), "-> distinct usable:", len(def_usable))

union = sorted(set(eng_usable) | set(def_usable))
print("UNION distinct usable:", len(union))
new_from_default = set(def_usable) - set(eng_usable)
print("Commands in default but not eng:", len(new_from_default))

# category breakdown if present
if "category" in eng.columns:
    print("\nENG category counts:")
    print(eng["category"].value_counts().to_string())

# overlap with nl2bash
nl2bash_path = r"E:/ai_malware_and_intrusion/final_project/scripts/raw/nl2bash.cm"
with open(nl2bash_path, encoding="utf-8", errors="replace") as f:
    nl2bash = {norm(line) for line in f if line.strip()}
print("\nnl2bash pool size (normalized):", len(nl2bash))

pool = union
random.seed(42)
sample = random.sample(pool, min(500, len(pool)))
hits = [c for c in sample if c in nl2bash]
pct = 100.0 * len(hits) / len(sample)
print(f"Overlap sample: {len(hits)}/{len(sample)} = {pct:.1f}%")
if hits[:10]:
    print("Example overlapping commands:", hits[:10])

# also case-insensitive overlap for information
nl2bash_low = {c.lower() for c in nl2bash}
hits_low = [c for c in sample if c.lower() in nl2bash_low]
print(f"Case-insensitive overlap: {len(hits_low)}/{len(sample)} = {100.0*len(hits_low)/len(sample):.1f}%")

# print random examples
print("\n20 random extracted commands:")
for c in random.sample(pool, 20):
    print("  |", c)

# length stats
lens = [len(c) for c in pool]
print("\nLength stats: min", min(lens), "median", sorted(lens)[len(lens)//2], "max", max(lens))

# save extracted
with open(f"{BASE}/extracted_commands.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(pool))
print("Saved to extracted_commands.txt")
