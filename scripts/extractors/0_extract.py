import re, random, sys

SRC = r"C:/Users/noham/AppData/Local/Temp/claude/E--ai-malware-and-intrusion/f054ff10-cc94-490f-951e-3a5f1e9cdb27/scratchpad/candidates/0_spignelon_bash_history/bash.txt"
NL2BASH = r"E:/ai_malware_and_intrusion/final_project/scripts/raw/nl2bash.cm"

def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

raw = open(SRC, encoding="utf-8", errors="replace").read().splitlines()
print("raw lines:", len(raw))

nonempty = [l for l in (norm_ws(x) for x in raw) if l]
print("non-empty (ws-collapsed):", len(nonempty))

# Filters: keep plausible standalone Linux shell one-liners
ps_pat = re.compile(r"^(Get-|Set-|New-|Remove-|Invoke-|Import-Module|powershell(\.exe)?\b)", re.I)
cmd_pat = re.compile(r"^([A-Za-z]:\\|cmd(\.exe)?\s|dir\s+[A-Za-z]:\\)", re.I)

dropped = {"too_long": 0, "no_alnum": 0, "powershell": 0, "cmdexe": 0, "comment": 0}
kept = []
for l in nonempty:
    if len(l) > 500:
        dropped["too_long"] += 1; continue
    if not re.search(r"[A-Za-z0-9]", l):
        dropped["no_alnum"] += 1; continue
    if ps_pat.match(l):
        dropped["powershell"] += 1; continue
    if cmd_pat.match(l):
        dropped["cmdexe"] += 1; continue
    if l.startswith("#"):
        dropped["comment"] += 1; continue
    kept.append(l)

print("dropped:", dropped)
print("kept (usable, non-distinct):", len(kept))

distinct = sorted(set(kept))
print("DISTINCT usable command lines (case kept, ws-collapsed):", len(distinct))

# first-token profile: sanity that these are shell commands
from collections import Counter
tok = Counter(l.split(" ", 1)[0] for l in distinct)
print("top 25 first tokens:", tok.most_common(25))
known = {"ls","cd","git","sudo","cat","vim","vi","nano","grep","find","rm","mkdir","touch","cp","mv","python","python3","pip","pip3","echo","curl","wget","tar","ssh","scp","docker","make","gcc","g++","chmod","chown","man","history","clear","pwd","exit","apt","apt-get","yum","dnf","top","htop","ps","kill","java","javac","node","npm","mount","umount","df","du","head","tail","less","more","sort","wc","awk","sed","which","whoami","uname","ifconfig","ip","ping","systemctl","service","source","export","./a.out","sh","bash","tmux","screen","ln","locate","tree","unzip","zip","gzip","gunzip","perl","ruby","go","cargo","mysql","psql","kubectl","helm","terraform","ansible","vagrant"}
frac_known = sum(c for t, c in tok.items() if t in known) / len(distinct)
print(f"fraction of distinct lines whose first token is a well-known unix command: {frac_known:.1%}")

# save extracted
out = SRC.replace("bash.txt", "extracted_distinct.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(distinct))
print("saved:", out)

# overlap with nl2bash
nl2 = set()
with open(NL2BASH, encoding="utf-8", errors="replace") as f:
    for line in f:
        n = norm_ws(line)
        if n:
            nl2.add(n.lower())
print("nl2bash distinct normalized lines:", len(nl2))

random.seed(42)
sample = random.sample(distinct, min(500, len(distinct)))
hits = sum(1 for s in sample if s.lower() in nl2)
print(f"overlap: {hits}/{len(sample)} = {hits/len(sample):.2%} of sample appears verbatim (lowercased+ws-collapsed) in nl2bash")

# examples
random.seed(7)
ex = random.sample(distinct, 12)
print("examples:")
for e in ex:
    print("  |", e)
