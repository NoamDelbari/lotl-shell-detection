# -*- coding: utf-8 -*-
import os, sys, re, yaml, json, random, collections

ROOT = sys.argv[1]; OUT = sys.argv[2]

files = []
for r, d, fs in os.walk(ROOT):
    for f in fs:
        if f.endswith(('.yaml', '.yml')): files.append(os.path.join(r, f))

PH = re.compile(r'#\{([^}]+)\}')
def resolve(cmd, args):
    defaults = {}
    for k, v in (args or {}).items():
        if isinstance(v, dict) and v.get('default') is not None:
            defaults[k] = str(v['default'])
    for _ in range(4):
        if '#{' not in cmd: break
        cmd = PH.sub(lambda m: defaults.get(m.group(1), m.group(0)), cmd)
    return cmd

FRAG = set(['do', 'done', 'fi', 'then', 'else', 'esac', ';;', '}', '{', ')', '(', ';', '&',
            'fi;', 'done;', 'EOF', 'EOL', 'do;', 'else;', 'then;', '"', "'", '[', ']', '],'])
OPENERS = re.compile(r'^\s*(if|for|while|until|case|elif|function)\b')
CLOSERS = re.compile(r'(;\s*(done|fi|esac)\b|\bdone\s*$|\bfi\s*$|\besac\s*$)')
STATUS_ECHO = re.compile(r'^\s*(echo|printf)\s+("[^"]*"|\'[^\']*\'|[A-Za-z0-9 ,.:!-]*)\s*$')
NL_HINT = re.compile(r'^\s*(Note|NOTE|This |The |Step \d|You |Please |Ensure |Make sure|Run the|See )')
CMDCHARS = re.compile(r'^[A-Za-z0-9_./$~"\'\[({@-]')

BSLASH = chr(92)

def join_continuations(text):
    out = []
    buf = ''
    for line in text.split('\n'):
        s = line.rstrip('\r')
        if buf:
            s = buf + ' ' + s.strip()
        if s.rstrip().endswith(BSLASH):
            buf = s.rstrip()[:-1].rstrip()
            continue
        buf = ''
        out.append(s)
    if buf: out.append(buf)
    return out

HD = re.compile(r'<<-?\s*[\'"]?([A-Za-z_][A-Za-z0-9_]*)[\'"]?')
def merge_heredocs(lines):
    out = []; i = 0
    while i < len(lines):
        m = HD.search(lines[i])
        if m:
            term = m.group(1); buf = [lines[i]]; i += 1
            while i < len(lines) and lines[i].strip() != term:
                buf.append(lines[i]); i += 1
            if i < len(lines):
                buf.append(lines[i]); i += 1
            out.append(' '.join(x.strip() for x in buf))
        else:
            out.append(lines[i]); i += 1
    return out

def ws(s): return re.sub(r'\s+', ' ', s).strip()

records = []
stats = collections.Counter()
for p in sorted(files):
    try:
        doc = yaml.safe_load(open(p, encoding='utf-8'))
    except Exception:
        stats['yaml_err'] += 1; continue
    if not isinstance(doc, dict): continue
    tech = doc.get('attack_technique')
    for t in doc.get('atomic_tests') or []:
        ex = t.get('executor') or {}
        if ex.get('name') not in ('bash', 'sh'): continue
        stats['bash_sh_tests'] += 1
        plats = [str(x).lower() for x in (t.get('supported_platforms') or [])]
        args = t.get('input_arguments') or {}
        raw = ex.get('command') or ''
        if not raw.strip(): continue
        txt = resolve(raw, args)
        lines = merge_heredocs(join_continuations(txt))
        for ln in lines:
            if ln.strip(): stats['raw_lines_nonempty'] += 1
            records.append({'technique': tech, 'test': t.get('name'),
                            'platforms': plats, 'line': ln})

kept = []
dropped = collections.Counter()
for r in records:
    s = ws(r['line'])
    if not s: dropped['empty'] += 1; continue
    if s in FRAG: dropped['fragment'] += 1; continue
    if re.match(r'^(done|fi|esac|do|then|else)\b', s): dropped['fragment'] += 1; continue
    if s.startswith('#') and not s.startswith('#{'): dropped['comment'] += 1; continue
    if '#{' in s: dropped['unresolved_placeholder'] += 1; continue
    if OPENERS.match(s) and not CLOSERS.search(s): dropped['open_block'] += 1; continue
    if not CMDCHARS.match(s): dropped['not_cmdlike'] += 1; continue
    if NL_HINT.match(s) and not re.search(r'[|;>/]', s): dropped['natural_lang'] += 1; continue
    if len(s) < 4: dropped['too_short'] += 1; continue
    r['clean'] = s
    r['status_echo'] = bool(STATUS_ECHO.match(s))
    kept.append(r)

n_status = sum(1 for r in kept if r['status_echo'])
dropped['status_echo (excluded from main pool)'] = n_status

def distinct(rs):
    seen = {}
    for r in rs:
        if r['clean'] not in seen: seen[r['clean']] = r
    return list(seen.values())

all_d = distinct(kept)
noecho = distinct([r for r in kept if not r['status_echo']])
lin = distinct([r for r in kept if (not r['status_echo']) and
                ('linux' in r['platforms'] or 'containers' in r['platforms'] or not r['platforms'])])
maconly = distinct([r for r in kept if (not r['status_echo']) and r['platforms'] == ['macos']])

print("=== STATS ===")
for k, v in stats.most_common(): print("  %s: %s" % (k, v))
print("=== DROPPED ===")
for k, v in dropped.most_common(): print("  %s: %s" % (k, v))
print("=== COUNTS (distinct, whitespace-collapsed, case preserved) ===")
print("  kept line instances:             %d" % len(kept))
print("  DISTINCT all kept:               %d" % len(all_d))
print("  DISTINCT excl. status-echo:      %d" % len(noecho))
print("  DISTINCT linux/containers:       %d" % len(lin))
print("  DISTINCT macos-only:             %d" % len(maconly))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    for r in noecho:
        f.write(json.dumps({'command': r['clean'], 'technique': r['technique'],
                            'platforms': r['platforms']}) + '\n')
with open(OUT.replace('.jsonl', '_linux.cm'), 'w', encoding='utf-8') as f:
    for r in lin: f.write(r['clean'] + '\n')
with open(OUT.replace('.jsonl', '_all.cm'), 'w', encoding='utf-8') as f:
    for r in noecho: f.write(r['clean'] + '\n')
print("wrote %s" % OUT)

random.seed(11)
print("")
print("=== 12 RANDOM EXAMPLES (linux pool) ===")
for r in random.sample(lin, min(12, len(lin))):
    print("[%s] %s" % (r['technique'], r['clean'][:180]))
