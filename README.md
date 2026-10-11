# vault-doctor

Read-only health check for an Obsidian vault (no network, no model calls, writes nothing).

Checks
- **Broken wikilinks** — `[[target]]`, `[[target|alias]]`, `[[target#heading]]`, `![[embed]]`, resolved Obsidian-style (path or bare filename, case-insensitive, attachments count). Code blocks / inline code are ignored.
- **Orphan notes** — notes with no inbound wikilink or markdown link (`Templates/`, root `README.md`, `MOC*` notes excluded).
- **Project cards** — `<projects-dir>/<name>/README.md`: stale `updated:` (>7 days), not linked from the MOC note, missing `현재 상태` / `작업 이력` sections.
- **Ledger ↔ card mismatch** (optional `--ledger`) — a markdown task list with `### [state] title` entries. An entry is linked to a card when the card folder name appears in it.
  - A: active entry whose card is >7 days stale
  - B: card `status: done` while its entry is still active

## Usage
```sh
python3 -I vault_doctor.py --vault ~/vault [--ledger ~/vault/tasks.md] \
    [--projects-dir Projects] [--moc "MOC - Projects.md"] [--json] [--limit 20]
python3 -I -m unittest discover -s tests
```
Entries whose state is `done` / `completed` / `완료` / `archived` count as finished; anything else is active.

## Safety
Read-only: no `open(..., 'w')`, no deletes. Output goes to stdout only.

---

## 한국어

Obsidian 볼트를 읽기 전용으로 점검합니다(네트워크·모델 호출·쓰기 없음).
깨진 위키링크, 고아 노트, 프로젝트 카드(7일 미갱신·MOC 링크 없음·섹션 누락), 그리고 선택적으로 작업 원장(`### [상태] 제목` 형식)과 카드 상태 불일치를 셉니다.
사용법은 위 명령과 같습니다. `--vault` 는 필수이고 `--ledger` 는 선택입니다.

## License
MIT
