# The tour

How to turn the reviewed units into a route, what the user sees, and how to walk them along it. Parts 1 and 2 are for Step 6, when the route is planned and written. Parts 3 and 4 are for Step 8, the walkthrough itself.

---

## Part 1 — Ordering the route

The route is good when the user never meets code whose inputs they don't understand yet, and spends their attention where the change matters.

1. **Contracts and data shapes first.** Schemas and migrations, types and interfaces, public function and API signatures, config. Everything else is written against them, and a reader who knows them reads the rest faster.
2. **Then the core logic, in the order it runs.** Start at the entry point (the request handler, the job, the command) and follow the calls down. A small new helper is read as a short detour at the point it is first called. A large one gets its own stop just before that point.
3. **Each unit's tests right after the unit.** The tests show which cases the author had in mind, and the gaps are easiest to see while the code is fresh.
4. **Supporting units next to what they support,** when they are small. Otherwise after the core.
5. **Mechanical units last, in one skim stop.** It lists every mechanical file with what it does (renamed, moved, reformatted) and how that was confirmed, and every left-out file with the reason. The user can see that nothing was skipped without having to read it.
6. **Stop size.** One unit, or a few small related ones. Aim for at most about 150 changed lines per stop; split a large unit by function or by file.
7. **With `--by-commit`,** the commits are sections, in order, and the rules above apply inside each one. When a later commit changes code from an earlier one, say so at both stops ("revisited at stop 7", "first seen at stop 3"). Code added in one commit and removed in a later one is worth a sentence: it's history the combined diff hides.

Every unit is on exactly one stop. Every kept finding is on the stop where its code is read.

---

## Part 2 — What the user sees

### The overview

Shown first, before any stop. It should fit on one screen.

```markdown
## Guided review: <target>

**What this change does:** <two or three sentences on behavior, from 2-summary.md>
**Size:** <n> commits · <n> files · +<a> −<d> · <n> hunks → <n> units → <n> stops
**Compared with the description:** <matches | differences, one line | no description>

### Important changes
1. <before → after> — `path:line`
2. …

### Findings ahead
🔴 <n> · 🟠 <n> · 🟡 <n> · 💬 <n>   (bugs <n> · logic <n> · readability <n> · cleanliness <n> · logging <n>)
**Branches:** <n> in the changed code · <n> removed from the base · <n> handled wrongly · <n> untested

### Route
| Stop | What you'll read | Rank | Findings |
|---|---|---|---|
| 1 | <title> | 🔴 core | B1, R2 |
| … | | | |
| 9 | Mechanical changes and left-out files | ⚪ | C3 |

Say `next` to start, or a stop number to jump there. Any time: `back`, `more`, `skip`, `rest`, `done`, or ask a question. To record your call on a finding: "agree B1", "B1 isn't a bug: …", "won't fix R2".
```

### A stop

```markdown
### Stop <n> of <total> — <title> · <rank>

**What changes:** <before → after, in behavior terms>
**Why it's here:** <one line: what it builds on, from earlier stops>

**Read, in this order:**
1. `path:12-48` — <what to notice there>
2. `path:90-110` — <…>

<the lines that matter most, as a diff excerpt of at most about 30 lines>

**How it works:** <two to four lines, to help the user read the code, not to replace reading it>

**Branches:** <n> · ✅ <n> · ❌ <n> · ❓ <n> · untested <n>
| # | Where | When | What happens | | Tested | Logged |
|---|---|---|---|---|---|---|
| b1 | `path:42` | amount ≤ 0 | raises ValueError | ✅ | yes | — |
| b2 | `path:47` | currency not in RATES (implicit else) | KeyError, 500 | ❌ B1 | no | — |
| r1 | was `path:60` | removed: retry on 503 | now fails at once | ❓ | — | — |

**Logging:** <failure branches logged <n> of <n> · audit-relevant actions recorded <n> of <n> · levels and sensitive fields: fine | see G…>

**Findings here:**
#### 🔴 [B1] <claim> — `path:line`
- **Input or state:** … · **What happens:** … · **Expected:** …
- **Suggested fix:** …

#### 🟡 [R2] <claim> — `path:line`
<now / clearer, as short code blocks> · **Why:** …

**Worth your judgment:** <one to three questions the code can't settle, about intent or product behavior, or "nothing here">
**Checked and fine:** <what was examined at this stop and found right, per lens, briefly>
```

Show every branch row for a core stop; it is how the user sees that all of the logic was accounted for. For a supporting stop with many simple branches, show the rows that are ❌, ❓ or untested and give the count of the rest, which `more` shows in full. Keep a stop to about 80 lines, splitting it if the branch table pushes past that. When a stop has no findings, say so plainly and keep the "checked and fine" line: it shows the stop was reviewed, not just narrated.

"Worth your judgment" is for what the guide couldn't settle, such as whether a behavior is what the product wants. Anything the guide could have checked, it should have checked in Step 5.

---

## Part 3 — Walking the user through

- **One stop per message, then wait.** End the turn after each stop. Don't run ahead; the user is reading.
- **Show each stop as written in `6-tour.md`.** If something the user said earlier changes a later stop (a finding withdrawn, a question answered), update the stop in the file first, then show it.
- **Keep `notes.md` current.** After every message, record the current stop and anything the user decided:

```
Current stop: <n> of <total>
Visited: 1, 2, 3 · Skimmed: — · Skipped: —

| ID | User's verdict | Their reason | Stop |
|---|---|---|---|
| B1 | agree | | 2 |
| R2 | won't fix | team prefers this style | 2 |

Raised by the user:
- [U1] <what they spotted> — `path:line` · checked: <result> · stop <n>

Questions asked: <one line each, with where the answer came from>
```

The commands the user can use:

| They say | You do |
|---|---|
| `next`, or anything like it | Show the next stop. |
| `back` | Show the previous stop again. |
| a stop number, or `go <n>` | Jump there. Stops passed over are marked skipped unless visited later. |
| `more` | Go deeper on the current stop: the whole function, its base version, its callers, the full branch table, or how a finding was verified. |
| `skip` | Mark the current stop skimmed and move on. |
| `rest` | Show all remaining stops in one message, then the wrap-up. |
| `done` | Go straight to the wrap-up. |

**Questions.** Answer from the code: open it again rather than relying on what you remember. Cite `path:line`. Then offer to continue.

**Verdicts.** When the user agrees, record it. When they dispute a finding, read the code again before replying:

- If they're right, say so plainly, mark the finding withdrawn in `5-verification.md` with their reason, and record it.
- If the code still shows the problem, show once the exact path or input that demonstrates it. Then record the user's call, whatever it is. The decision is theirs.

**When the user spots something,** check it as Step 5 would check any finding, tell them the result, and record it under "Raised by the user" with an ID `U1`, `U2`, … If it's confirmed, it goes in the wrap-up beside the guide's findings.

---

## Part 4 — The wrap-up

After the last stop, or on `done`:

```markdown
## Review wrap-up: <target>

**Stops:** <n> visited · <n> skimmed · <n> skipped: <stop numbers and titles>

### Findings
| ID | Finding | Rating | Your verdict |
|---|---|---|---|
| B1 | <claim> — `path:line` | 🔴 | agree |
| R2 | … | 🟡 | won't fix: <reason> |
| L1 | … | 🟠 | not yet discussed |

### Untested branches
| Branch | Where | Risk | Your call |
|---|---|---|---|
| <condition> | `path:line` | <error path, money, permissions, data, or low> | <test it | leave it | not yet discussed> |

### Logging
<failure branches logged <n> of <n> · audit-relevant actions recorded <n> of <n> · open logging findings, or "No gaps.">

### Raised by you
- <ID, claim, result of the check; or none>

### Not read together
<units on skipped stops, so the user knows what they haven't looked at; or "Every stop was visited.">

### Suggested outcome
✅ Approve | ⚠️ Approve after changes | ❌ Request changes — <one sentence, based on the 🔴 and 🟠 findings the user agreed with or didn't dispute>

**Limits:** <what couldn't be run or read, mode and models used>
**Work files:** `<work>`
```

The suggested outcome follows the user's verdicts: a 🔴 finding the user withdrew doesn't count against the change. Then offer the follow-ups from SKILL.md's "After the walkthrough".

With `--doc`, the wrap-up in `guide.md` has the findings table with the "Your verdict" column left blank, for the user to fill in as they read.
