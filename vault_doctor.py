#!/usr/bin/env python3
"""vault-doctor v0.1 — Obsidian 볼트 읽기 전용 건강검진 (모델 호출 0, 네트워크 0).

Checks: broken wikilinks / orphan notes / task ledger <-> project card mismatch / card freshness.
Read-only: writes nothing to the vault or ledger (stdout only).
"""
import argparse, datetime, json, os, re, sys
from collections import Counter, defaultdict

EXCL_DIRS = {'.obsidian', '.git', '.trash', 'node_modules'}
WIKI = re.compile(r'!?\[\[([^\]\n]+?)\]\]')
MDLINK = re.compile(r'\]\(([^)\s]+?\.md)(?:#[^)]*)?\)')
FENCE = re.compile(r'```.*?```', re.S)
INLINE = re.compile(r'`[^`\n]*`')
ENTRY = re.compile(r'^### \[([^\]\n]+)\]\s*(.+)$', re.M)
DONE = {'done', 'completed', '완료', 'archived'}
PROJECTS_DIR = 'Projects'
MOC_PATH = 'MOC - Projects.md'


def readtext(p):
    with open(p, encoding='utf-8', errors='ignore') as fh:
        return fh.read()


def strip_code(t):
    return INLINE.sub('', FENCE.sub('', t))


def scan(vault):
    notes, files = [], []
    for root, dirs, fs in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in EXCL_DIRS]
        for f in fs:
            rel = os.path.relpath(os.path.join(root, f), vault)
            files.append(rel)
            if f.endswith('.md'):
                notes.append(rel)
    return sorted(notes), files


def build_index(files):
    by_path, by_name = {}, defaultdict(list)
    for rel in files:
        low = rel.lower()
        by_path[low] = rel
        if low.endswith('.md'):
            by_path[low[:-3]] = rel
        base = os.path.basename(low)
        by_name[base].append(rel)
        if base.endswith('.md'):
            by_name[base[:-3]].append(rel)
    return by_path, by_name


def resolve(target, by_path, by_name):
    t = target.split('|')[0].split('#')[0].strip().replace('\\', '')
    if not t:
        return '#self'
    low = t.lower().lstrip('/')
    if '/' in low:
        return by_path.get(low) or by_path.get(low + '.md')
    hits = by_name.get(low) or by_name.get(low + '.md')
    return hits[0] if hits else None


def links(vault, notes, by_path, by_name):
    broken = Counter()
    broken_from = defaultdict(set)
    inbound = defaultdict(set)
    total = 0
    for rel in notes:
        try:
            t = strip_code(readtext(os.path.join(vault, rel)))
        except OSError:
            continue
        for m in WIKI.finditer(t):
            total += 1
            r = resolve(m.group(1), by_path, by_name)
            if r is None:
                k = m.group(1).split('|')[0].split('#')[0].strip()
                broken[k] += 1
                broken_from[k].add(rel)
            elif r != '#self' and r != rel:
                inbound[r].add(rel)
        for m in MDLINK.finditer(t):
            p = m.group(1)
            if '://' in p:
                continue
            cand = os.path.normpath(os.path.join(os.path.dirname(rel), p)).lower()
            r = by_path.get(cand) or by_path.get(p.lower().lstrip('/'))
            if r and r != rel:
                inbound[r].add(rel)
    return total, broken, broken_from, inbound


def orphan_excluded(rel):
    return rel.startswith('Templates/') or rel == 'README.md' or os.path.basename(rel).startswith('MOC')


def frontmatter(t):
    m = re.match(r'---\n(.*?)\n---', t, re.S)
    fm = m.group(1) if m else ''
    upd = re.search(r'updated:\s*"?(\d{4}-\d{2}-\d{2})', fm or t)
    st = re.search(r'^status:\s*"?([^"\n]+)', fm, re.M)
    return (upd.group(1) if upd else None), (st.group(1).strip().lower() if st else None)


def cards(vault, today, projects_dir=None, moc_path=None):
    projects_dir = projects_dir or PROJECTS_DIR
    moc_p = os.path.join(vault, moc_path or MOC_PATH)
    moc = readtext(moc_p) if os.path.exists(moc_p) else ''
    out = {}
    pdir = os.path.join(vault, projects_dir)
    for name in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
        p = os.path.join(pdir, name, 'README.md')
        if not os.path.isfile(p):
            continue
        s = readtext(p)
        upd, st = frontmatter(s)
        age = (today - datetime.date.fromisoformat(upd)).days if upd else None
        issues = []
        if age is None:
            issues.append('updated 없음')
        elif age > 7:
            issues.append(f'{age}일 미갱신')
        if f'{projects_dir}/{name}/README' not in moc:
            issues.append('MOC 링크 없음')
        for sec in ('현재 상태', '작업 이력'):
            if sec not in s:
                issues.append(f"'{sec}' 섹션 없음")
        out[name] = {'updated': upd, 'age': age, 'status': st, 'issues': issues}
    return out


def ledger(path):
    if not path or not os.path.exists(path):
        return []
    t = readtext(path)
    ms = list(ENTRY.finditer(t))
    items = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(t)
        nxt = t.find('\n## ', m.end())
        if 0 <= nxt < end:
            end = nxt
        items.append({'state': m.group(1), 'title': m.group(2).strip(), 'body': t[m.start():end]})
    return items


def cross(items, cardinfo):
    active = [x for x in items if x['state'].strip().lower() not in DONE]
    linked, unlinked, a, b, used = 0, [], [], [], set()
    for x in active:
        body = x['body'].lower()
        hit = [c for c in cardinfo if re.search(r'(?<![\w-])' + re.escape(c.lower()) + r'(?![\w-])', body)]
        if not hit:
            unlinked.append(x['title'][:80])
            continue
        linked += 1
        for c in hit:
            used.add(c)
            ci = cardinfo[c]
            if ci['age'] is not None and ci['age'] > 7:
                a.append({'entry': x['title'][:80], 'state': x['state'], 'card': c, 'card_age_days': ci['age']})
            if ci['status'] in DONE:
                b.append({'entry': x['title'][:80], 'state': x['state'], 'card': c, 'card_status': ci['status']})
    return {'active_entries': len(active), 'linked_entries': linked, 'mismatch_A_stale_card': a,
            'mismatch_B_done_card_active_entry': b, 'info_entries_without_card': len(unlinked),
            'info_cards_without_entry': sorted(set(cardinfo) - used)}


def run(vault, ledger_path, today=None, projects_dir=None, moc_path=None):
    today = today or datetime.date.today()
    notes, files = scan(vault)
    by_path, by_name = build_index(files)
    total, broken, broken_from, inbound = links(vault, notes, by_path, by_name)
    orphans = [n for n in notes if not inbound.get(n) and not orphan_excluded(n)]
    by_folder = Counter(n.split('/')[0] if '/' in n else '(root)' for n in orphans)
    ci = cards(vault, today, projects_dir, moc_path)
    return {
        'vault': vault, 'today': today.isoformat(),
        'notes': len(notes), 'files': len(files),
        'wikilinks_total': total,
        'broken_links_occurrences': sum(broken.values()),
        'broken_links_unique_targets': len(broken),
        'broken': [{'target': k, 'count': v, 'from': sorted(broken_from[k])[:5]} for k, v in broken.most_common()],
        'orphans_count': len(orphans), 'orphans_by_folder': dict(by_folder.most_common()), 'orphans': orphans,
        'cards': len(ci), 'cards_warn': sum(1 for v in ci.values() if v['issues']), 'card_detail': ci,
        'ledger': cross(ledger(ledger_path), ci),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description='Obsidian 볼트 읽기 전용 건강검진(깨진 링크·고아 노트·원장↔카드)')
    ap.add_argument('--vault', required=True, help='vault root, e.g. ~/vault')
    ap.add_argument('--ledger', default=None, help='optional task ledger markdown (### [state] title entries)')
    ap.add_argument('--projects-dir', default=PROJECTS_DIR, help='folder holding <project>/README.md cards (default: Projects)')
    ap.add_argument('--moc', default=MOC_PATH, help='index note that should link every card (default: "MOC - Projects.md")')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--limit', type=int, default=15)
    a = ap.parse_args(argv)
    r = run(os.path.expanduser(a.vault), a.ledger and os.path.expanduser(a.ledger), None, a.projects_dir, a.moc)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    L = r['ledger']
    print(f"vault-doctor {r['today']} — {r['vault']}")
    print(f"노트 {r['notes']} / 파일 {r['files']} / 위키링크 {r['wikilinks_total']}개")
    print(f"깨진 위키링크: 출현 {r['broken_links_occurrences']} / 고유 대상 {r['broken_links_unique_targets']}")
    for x in r['broken'][:a.limit]:
        print(f"  - [[{x['target']}]] ×{x['count']} ← {', '.join(x['from'][:2])}")
    print(f"고아 노트: {r['orphans_count']} / 노트 {r['notes']}  폴더별 {r['orphans_by_folder']}")
    print(f"카드: {r['cards']} / 경고 {r['cards_warn']}")
    for k, v in r['card_detail'].items():
        if v['issues']:
            print(f"  WARN {k}: {', '.join(v['issues'])}")
    print(f"원장: 진행중·대기 {L['active_entries']} / 카드 연결 {L['linked_entries']} / 불일치A(카드 7일+) {len(L['mismatch_A_stale_card'])} / 불일치B(카드 완료·항목 진행) {len(L['mismatch_B_done_card_active_entry'])}")
    for x in L['mismatch_A_stale_card'] + L['mismatch_B_done_card_active_entry']:
        print(f"  - {x}")
    print(f"  정보: 카드 없는 항목 {L['info_entries_without_card']} / 항목 없는 카드 {L['info_cards_without_entry']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
