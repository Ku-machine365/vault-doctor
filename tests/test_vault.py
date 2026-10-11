"""합성 볼트 테스트(네트워크 없음). 실행: python3 -I -m unittest discover -s tests"""
import datetime, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vault_doctor import run

FILES = {
    'README.md': '[[a]] [[Projects/p1/README]]',
    'a.md': '[[b|별칭]] [[missing1]] [[missing1#x]] ![[img.png]] [[#self]] `[[incode]]`\n```\n[[fenced]]\n```',
    'b.md': '[[a]] [[sub/missing2]]',
    'sub/c.md': 'no links',                      # 고아
    'd.md': '[링크](sub/e.md)',                  # 고아(아무도 d를 안 가리킴)
    'sub/e.md': '',                              # md 링크로 연결됨
    'img.png': '',
    'Templates/t.md': '',                        # 고아 제외
    'MOC - Projects.md': '[[Projects/p1/README]] Projects/p2/README',
    'Projects/p1/README.md': '---\nupdated: "2026-09-01"\nstatus: done\n---\n## 현재 상태\n## 작업 이력',
    'Projects/p2/README.md': '---\nupdated: "2026-10-10"\n---\n## 현재 상태\n## 작업 이력\n[[README]]',
}
LEDGER = '### [진행중] p1 작업\n- 내용\n### [대기] 기타 일\n- x\n### [완료] p2 끝\n'

class Vault(unittest.TestCase):
    def test_counts(self):
        with tempfile.TemporaryDirectory() as d:
            for rel, t in FILES.items():
                p = os.path.join(d, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, 'w').write(t)
            lp = os.path.join(d, 'ledger.txt'); open(lp, 'w').write(LEDGER)
            r = run(d, lp, datetime.date(2026, 10, 11))
        self.assertEqual(r['broken_links_occurrences'], 3)   # missing1 ×2, sub/missing2
        self.assertEqual(r['broken_links_unique_targets'], 2)
        self.assertEqual(sorted(r['orphans']), ['Projects/p2/README.md', 'd.md', 'sub/c.md'])
        self.assertEqual(r['cards'], 2)
        L = r['ledger']
        self.assertEqual(L['active_entries'], 2); self.assertEqual(L['linked_entries'], 1)
        self.assertEqual(len(L['mismatch_A_stale_card']), 1)
        self.assertEqual(len(L['mismatch_B_done_card_active_entry']), 1)

if __name__ == '__main__':
    unittest.main()
