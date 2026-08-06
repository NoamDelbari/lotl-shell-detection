import os, re, random, sys

BASE = r"C:/Users/noham/AppData/Local/Temp/claude/E--ai-malware-and-intrusion/f054ff10-cc94-490f-951e-3a5f1e9cdb27/scratchpad/candidates/6_tldr-pages_tldr__command_example_lines_"
PAGES = os.path.join(BASE, "tldr-main", "pages")
UNIX_DIRS = ["common", "linux", "osx", "freebsd", "netbsd", "openbsd", "sunos"]

example_re = re.compile(r"^`(.+)`\s*$")
ph_re = re.compile(r"\{\{(.*?)\}\}")

def ws_collapse(s):
    return re.sub(r"\s+", " ", s).strip()

raw_templates = set()
concrete = set()
n_files = 0
n_lines_total = 0

for d in UNIX_DIRS:
    root = os.path.join(PAGES, d)
    for dirpath, _, files in os.walk(root):
        for f in files:
            if not f.endswith(".md"):
                continue
            n_files += 1
            with open(os.path.join(dirpath, f), encoding="utf-8") as fh:
                for line in fh:
                    m = example_re.match(line.strip())
                    if not m:
                        continue
                    n_lines_total += 1
                    tmpl = ws_collapse(m.group(1))
                    if not tmpl:
                        continue
                    raw_templates.add(tmpl)
                    # substitute {{placeholder}} -> inner text (tldr placeholders
                    # usually carry example values like path/to/file, package)
                    conc = ph_re.sub(lambda mm: mm.group(1), tmpl)
                    conc = ws_collapse(conc)
                    # drop anything with leftover braces or empty after subst
                    if not conc or "{{" in conc or "}}" in conc:
                        continue
                    concrete.add(conc)

print("files parsed:", n_files)
print("example lines total (with dups):", n_lines_total)
print("distinct raw template lines:", len(raw_templates))
print("distinct concrete lines after placeholder substitution:", len(concrete))

out = os.path.join(BASE, "tldr_commands_concrete.txt")
with open(out, "w", encoding="utf-8") as fh:
    for c in sorted(concrete):
        fh.write(c + "\n")
print("wrote:", out)

# overlap with nl2bash
nl2bash_path = r"E:/ai_malware_and_intrusion/final_project/scripts/raw/nl2bash.cm"
nl2bash = set()
with open(nl2bash_path, encoding="utf-8", errors="replace") as fh:
    for line in fh:
        nl2bash.add(ws_collapse(line))

random.seed(42)
pool = sorted(concrete)
sample = random.sample(pool, min(500, len(pool)))
hits = sum(1 for s in sample if s in nl2bash)
print(f"overlap sample: {hits}/{len(sample)} = {100.0*hits/len(sample):.2f}%")

# also check overlap of raw templates just in case
hits_t = sum(1 for s in random.sample(sorted(raw_templates), min(500, len(raw_templates))) if s in nl2bash)
print(f"template overlap sample: {hits_t}/500")

print("\n5 examples (concrete):")
for s in random.sample(pool, 5):
    print("  ", s)
