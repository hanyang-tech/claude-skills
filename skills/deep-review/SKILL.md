---
name: deep-review
description: Thorough, multi-angle review of code changes. First reconstructs the intent of the change (following ticket links, and interviewing the user when requirements are missing or the change is high-risk), then reviews it through independent lenses (correctness vs. intent, edge cases, failure modes, concurrency/state, security, contracts/compatibility, performance, tests, omissions), verifies every finding against the code, and reports only confirmed bugs and risks with concrete failure scenarios. Use when the user asks for a deep, thorough, or careful review of a diff, branch, commit range, or PR, wants to catch bugs before merging, or invokes /deep-review [target] [--thorough] [--spec <path>] [--no-ask] [-- <requirements>].
---

# Deep Review

Review a change the way a strong senior engineer does: understand **what the author was trying to do** first, then attack the change from several independent angles, then **prove** each suspected issue before reporting it.

Target: `$ARGUMENTS` (see Step 1 for accepted forms). This skill is **read-only**: never edit, commit, or push unless the user explicitly asks after the review.

## Principles

- **Intent before critique.** A bug is a gap between what the code does and what it was meant to do. You can't find that gap without writing down the intent first.
- **Read beyond the diff.** Most real bugs live at the boundary between changed and unchanged code: callers that weren't updated, invariants the old code relied on, a sibling code path that got missed.
- **Different angles, independently.** Each lens asks a different question. Don't let one lens's conclusion ("looks correct") stop another's search.
- **Every finding needs a failure scenario.** Concrete input/state → concrete wrong outcome. If you can't construct one, it's a question for the author, not a finding.
- **Signal over volume.** Five verified bugs beat thirty style nits. Style and taste go last, and only if they matter.

## Step 1 — Scope the change

Resolve the target from `$ARGUMENTS`:

| Argument | What to review |
|---|---|
| *(empty)* | Uncommitted work: `git diff HEAD` plus untracked files (`git status --porcelain`). If the tree is clean, the current branch vs. its merge-base with the default branch. |
| PR number or URL | `gh pr view <n> --json title,body,baseRefName,headRefName,files,commits` and `gh pr diff <n>`. Also read linked issues and existing review comments. |
| Branch name | `git diff $(git merge-base <default> <branch>)..<branch>` |
| Commit / range (`abc123`, `a..b`) | `git show` / `git diff a..b` |
| File or directory path | The pending changes under that path; if none, review the path's current code as-is. |

**Options** (strip them before resolving the target):

| Option | Effect |
|---|---|
| `--thorough` | Forces fan-out mode (Step 4) even for small changes and runs every subagent on Opus (see [Model assignment](#model-assignment)). |
| `--spec <path>` | A requirements, ticket, or design file to treat as the authoritative intent. |
| `-- <text>` | Everything after a bare `--` is the requirements in the user's words, e.g. `/deep-review 123 -- refunds must be blocked after 30 days`. |
| `--no-ask` | Never pause to ask questions (for unattended or CI runs). Fall back to **assumed** intent, clearly flagged. |

Find the default branch with `git symbolic-ref refs/remotes/origin/HEAD` (fall back to `main`/`master`). Then collect:

- `git diff --stat` for size and shape, and the full diff.
- Commit messages in the range (`git log --format='%h %s%n%b' <range>`).
- PR description, linked issue/ticket, and any design doc the change references.

If the target is ambiguous or empty in every interpretation, ask the user what to review instead of guessing.

## Step 2 — Reconstruct the intent

Before judging anything, write a short **Intent Statement** (keep it for the report):

1. **Goal** — the problem being solved or feature being added, in one or two sentences.
2. **Expected behavior change** — what should behave differently after this change, and for whom (users, callers, other services, data).
3. **Explicit non-goals / should-stay-the-same** — behavior that must be preserved.
4. **Invariants and assumptions** — what the new code assumes about inputs, state, ordering, environment.
5. **Approach** — how the author chose to implement it, in a sentence.

Sources, in order of authority: requirements the user gave (`--spec`, `-- <text>`, or answers in Step 2b) → PR/issue/ticket text → commit messages → tests added or changed (tests reveal intended behavior) → names and comments → the code itself. When sources disagree (e.g., PR says "only admins", code checks nothing), that disagreement is itself a finding. Tag each part of the Intent Statement with where it came from: `(user)`, `(spec)`, `(PR)`, `(ticket)`, `(commits)`, `(tests)`, or `(inferred)`.

**Follow ticket references before judging the evidence.** Look for issue keys and links in the PR body, branch name, and commit messages (`JIRA-123`, `ENG-42`, `#123`, tracker URLs). Open them with whatever is available: `gh issue view` for GitHub issues, or a connected Jira, Linear, or other tracker tool if the session has one. Also check the repo for a referenced design doc (`docs/`, ADRs, RFCs). Record any reference you couldn't open.

**Grade the intent evidence:**

- **Strong**: the user's requirements, a spec, or a PR or ticket that describes the expected behavior (not just "fix bug").
- **Weak**: only commit messages, branch names, or tests to go on, or a referenced ticket that couldn't be opened.
- **None**: nothing but the code itself. Reading the intent from the code is circular: a correct implementation of the wrong requirement looks fine.

### Step 2b — Interview the user when the intent is weak

Ask the user, rather than guessing, when **any** of these hold:

- The evidence is **Weak** or **None**.
- A referenced ticket or doc couldn't be opened.
- The change is **high-risk** (as defined under [Model assignment](#model-assignment); judge it from the diff's paths and contents). Even with strong evidence, ask the unwritten-rules question below, because those rules are rarely written in a PR.

Skip the interview when the evidence is **Strong**, the change isn't high-risk, and no reference is unreachable. Also skip it under `--no-ask`, or when there's no interactive user (headless or CI runs). Then continue with **assumed** intent and say so at the top of the report.

**How to ask.** Use the AskUserQuestion tool once, with at most 4 questions and only the ones that apply. Build every option from what you actually saw in the diff. Don't ask open-ended "what does this do?" questions: offer your best reading so the user can confirm it in one click. The tool always adds an "Other" option for free-text answers. If AskUserQuestion isn't available, ask the same questions in chat and wait for the reply.

1. **Goal** (evidence Weak/None). "What is this change meant to do?" Offer your best inference, marked "(Recommended)", and one or two plausible alternative readings of the same diff. Add an option like "I'm not the author, review against your best reading".
2. **Must stay the same** (multiSelect). "What must this change *not* break?" Offer options specific to this diff, such as "Existing API responses stay backward compatible", "Old stored records remain readable", "`/v1/orders` behavior is unchanged for non-admin users".
3. **Unwritten rules** (multiSelect; always asked for high-risk changes). "Which rules must this code never violate?" Offer domain invariants that fit the diff, such as "A payment is never charged twice (retries are idempotent)", "Users only ever see their own tenant's data", "Migrations must be safe to run on a live database".
4. **Unreachable reference** (only if a ticket or doc couldn't be opened). "I couldn't open `JIRA-123`. What does it require?" Offer "Continue without it" and "I'll paste the requirements (use Other)".

**Using the answers.** Fold them into the Intent Statement, tagged `(user)`. Selected must-stay-the-same items and unwritten rules become explicit invariants. Every lens checks the change against them (pass them to subagents in their brief), and a violation is at least a Major finding. If the user picks "review against your best reading" or skips, keep the inference but label it **assumed**. Ask once per review; don't come back with follow-up questions unless an answer contradicts the code in a way that changes what you'd review.

## Step 3 — Build context

Read enough to judge the change, not just the hunks:

- **Full content** of each changed function/class, and the whole file when it's small.
- **Callers** of every changed or removed function, method, field, route, config key, or event (use Grep across the repo). Did the signature, return shape, error behavior, or timing change for any of them?
- **Siblings**: similar code paths that should have received the same change (other handlers, other DB backends, the sync and async versions, the web and mobile clients).
- **Tests** touching the changed code — existing and new.
- **Contracts**: schemas, migrations, API specs, serialization, feature flags, env/config.
- Project conventions: `CLAUDE.md`, `CONTRIBUTING.md`, lint config — so you judge against the project's own standards.

For a large change, map it first: group files into logical units (e.g., "schema + migration", "API handler", "client") and note which units are risky (data, auth, money, concurrency, public API) — spend the most effort there.

## Step 4 — Review through independent lenses

Apply every lens in [references/lenses.md](references/lenses.md). Each lens has its own guiding question and checklist:

1. **Intent & logic** — does the code actually achieve the stated intent?
2. **Edge cases & inputs** — what inputs or states break it?
3. **Failure modes & error handling** — what happens when something it depends on fails?
4. **State, concurrency & ordering** — what happens under interleaving, retries, or repeated calls?
5. **Security & trust boundaries** — can an untrusted party abuse this?
6. **Contracts, data & compatibility** — what breaks for existing callers, stored data, or other deployed versions?
7. **Performance & resources** — what happens at 100× the data or traffic?
8. **Tests** — would the tests catch it if this change were subtly wrong?
9. **Omissions** — what *should* have changed but didn't?
10. **Maintainability** — only issues that will plausibly cause future bugs.

**Choose the execution mode by size:**

- **Small change** (roughly < 300 changed lines, ≤ 10 files, and no `--thorough`): run the lenses yourself, one pass per lens. Actually re-read the code for each lens; don't tick lenses off from memory of the first read.
- **Large or high-risk change, or `--thorough`**: fan out in parallel with the Agent tool (`general-purpose` agents, all launched in **one message**), one agent per lens group, each with the `model` set per the table in [Model assignment](#model-assignment):
  - A: Intent & logic + Edge cases + Omissions
  - B: Failure modes + State/concurrency/ordering
  - C: Security + Contracts/data/compatibility
  - D: Performance + Tests + Maintainability

  **Use fresh-context agents, never forks.** Forks that inherit this conversation also inherit your first impressions and lower the independence of each lens. A fresh agent sees only its brief, so it reads the code with fresh eyes. The brief must be self-contained but curated. Include:
  - the Intent Statement with its source tags and **assumed** parts marked, plus the user's must-stay-the-same items and unwritten rules from Step 2b, labelled as invariants to check
  - the exact git/gh command to get the diff, and the repo path
  - the context map from Step 3: risky units, callers, sibling paths, contracts, and project conventions files
  - the full text of its lens sections, copied from `references/lenses.md`
  - this instruction: *"Read-only. Report candidate findings as: file:line, lens, one-line claim, concrete failure scenario (input/state → wrong outcome), evidence (code you read), confidence high/medium/low. Also list what you checked and found sound. Do not report style nits."*

  Do **not** include your own suspicions, candidate findings, or "looks fine" judgments in the brief. Those anchor the agent and defeat the purpose of an independent angle. Agent output isn't visible to the user, so you merge and relay it.

### Model assignment

Always pass `model` explicitly on each Agent call; don't let subagents silently inherit the session's model. Put the reasoning-heavy work on Opus and the checklist-style reading on Sonnet, since reading files is where most subagent tokens go.

| Role | Default | With `--thorough` | Why |
|---|---|---|---|
| Main agent: intent, context map, merging, severity, verdict | the session's model (Opus recommended) | same | A wrong Intent Statement misleads every lens. There's only one of these, so a stronger model costs little. |
| A: Intent & logic + Edge cases + Omissions | `opus` | `opus` | Comparing "what was meant" with "what the code does" is the hardest reasoning in the review. |
| B: Failure modes + State/concurrency/ordering | `opus` | `opus` | Races and partial-failure bugs need reasoning about interleavings the code doesn't show. |
| C: Security + Contracts/data/compatibility | `opus` if the change is **high-risk**, else `sonnet` | `opus` | Common injection and secret checks are pattern-matching. Authorization gaps and rollout compatibility need judgment. |
| D: Performance + Tests + Maintainability | `sonnet` | `opus` | Mostly pattern-spotting, where a wrong call does the least damage. |
| Skeptic verifiers (Step 5) | `opus` | `opus` | Few in number. Wrongly confirming or dismissing a Blocker is the costliest error in the review. |

**High-risk** means the change touches any of: authentication or authorization, payments or money, cryptography or secrets, database schema or migrations, public API or event contracts, or data deletion. Decide this from the context map in Step 3, and state which models you used under "Coverage & limits" in the report.

If the session isn't running on Opus, tell the user once, at the start, that the main-agent steps would be more reliable on Opus. Then continue; don't block on it.

## Step 5 — Verify every candidate finding

Treat each candidate as a hypothesis and try to **disprove** it before reporting:

- Re-read the exact code path end to end, including the unchanged code around it. Is the "bad" input actually reachable, or validated upstream? Is the "missing" check done by a caller, middleware, framework, or DB constraint?
- Check whether an existing test already covers the scenario and passes.
- When cheap and safe, get empirical evidence: run the relevant existing tests, or a tiny throwaway script/REPL snippet in the scratchpad that exercises the scenario. Never run anything destructive, touch production resources, or modify the working tree to do this.
- Merge duplicates (the same root cause found by two lenses is one finding).
- **Independent skeptic (whenever you fanned out in Step 4).** For each candidate you'd rate Blocker or Major, launch a *fresh-context* `general-purpose` agent with `model: "opus"`, all in parallel. It should not be the agent that found the issue. Give it only the claim, the file:line, the failure scenario, and the diff command. Instruct it: *"Try to disprove this. Trace the code path, look for upstream validation, callers, framework guarantees, or tests that make it impossible. Reply CONFIRMED, PLAUSIBLE, or REFUTED with the evidence."* A finder is biased towards its own finding; a fresh skeptic isn't. If the skeptic refutes a finding and you disagree, re-check the code yourself and resolve it on evidence.

Then classify:

- **Confirmed** — you traced the path (or reproduced it) and the failure scenario holds.
- **Plausible** — strong reasoning, but depends on something you couldn't verify (runtime config, external service behavior). Say what would confirm it.
- **Dropped** — disproved. Don't report it, but if it was a tempting false alarm, you may mention it under "Checked and sound" so the author knows it was considered.

Low-confidence ideas that you couldn't turn into a failure scenario become **Questions for the author**, not findings.

## Step 6 — Assign severity

- **🔴 Blocker** — will cause incorrect behavior, data loss/corruption, a security hole, or an outage in realistic use. Must fix before merge.
- **🟠 Major** — a real bug in a less common path, a broken contract for some callers, a missing test for risky logic, or a significant performance regression.
- **🟡 Minor** — correct today but fragile, a narrow edge case with low impact, or a maintainability issue likely to cause future bugs.
- **💬 Nit** — optional polish. Include at most a handful, and only if the user asked for a full review.

Severity reflects impact × likelihood, not how clever the finding is.

## Step 7 — Report

Use this structure:

```markdown
## Deep Review: <target>

**Verdict:** ✅ Ready to merge | ⚠️ Merge after fixes | ❌ Needs rework
<one or two sentences explaining the verdict>

### Intent (as understood)
<Intent Statement from Step 2, condensed, with each part's source tag; mark any **assumed** parts>
**Evidence:** Strong | Weak | None · <whether the user was interviewed, and any ticket/doc that couldn't be opened>

### Findings
#### 🔴 [B1] <short claim> — `path/to/file.ext:123`
- **Lens:** <lens name> · **Status:** Confirmed | Plausible
- **Problem:** <what is wrong, one or two sentences>
- **Failure scenario:** <concrete input/state → concrete wrong outcome>
- **Evidence:** <the code path traced, test run, or repro output>
- **Suggested fix:** <specific change; short code snippet if it helps>

#### 🟠 [M1] ...
#### 🟡 [m1] ...

### Questions for the author
- <things that depend on intent you couldn't determine>

### Checked and sound
- <areas/lenses examined with no issues, e.g. "Migration is reversible and backfills existing rows">

### Coverage & limits
<what was reviewed, what wasn't (e.g. generated files, vendored code), anything you couldn't run>
<mode (inline or fan-out) and which model ran each lens group and the skeptic checks>
```

Order findings by severity, then by confidence. Link every file reference as `path:line`. If there are no findings, say so plainly and let "Checked and sound" show the review was real — never invent findings to look thorough.

## After the review

Offer, don't assume, next steps:

- Fix the confirmed findings (then re-verify only the changed areas).
- Post findings as PR comments with `gh` — only on explicit request, since it publishes on the user's behalf. Show the exact comments first.
- Add tests for the failure scenarios found.
