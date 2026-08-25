# ROOT Kata curriculum contract

This file is the durable contract for adding curriculum, including autonomous agent work.

The implementation should stay small. Curriculum growth must not require new runtime architecture.

## Authoritative syllabus

The curriculum has two deliberate layers:

- `curriculum/plan.json` — macro syllabus, milestone order, source baseline and broad scope;
- `curriculum/triads/<milestone>.csv` — **authoritative exercise-level queue** for the corresponding core milestone.

Routine autonomous workers execute these files; they do not redesign them.

`AGENTS.md` is the short operational entry point for future agents.

## Learning model

Use source courses as evidence of **competencies**, not as files to split mechanically.

Prefer, when useful:

**Manipulate → Observe → Predict → Code**

A kata should normally teach or test one causal idea and take roughly 5–15 minutes.

A high-value topic is normally revisited as:

```text
normal use
    ↓
limitation / misconception
    ↓
integration with another learned idea
```

### `normal`

The learner performs the ordinary useful operation and sees its direct consequence. The challenge should be the concept, not boilerplate.

### `limitation`

The learner encounters a real boundary, failure mode, semantic trap or misleading assumption. This is not merely the same exercise with bigger numbers.

Examples include histogram under/overflow, wrong TFile keys, missing branches, strict cut boundaries, repeated lazy-event-loop execution, mask/object correspondence, fit-model mismatch, unwanted Snapshot schema or thread-unsafe helper state.

The feedback should make the cause visible.

### `integration`

The learner combines the concept with something already understood in a small realistic task. Examples include selection + histogram, TTree + RDataFrame, object mask + derived pT + histogram, Snapshot + second-stage analysis, cutflow + final distribution, or a shared analysis across two samples.

Integration increases transfer distance, not code length for its own sake.

This triad is a default learning pattern, not a quota. Reviewers should merge or redesign a triad when the three encounters would be artificial duplicates. Routine workers follow the planned rows.

## Difficulty means transfer distance

`curriculum.transfer_level` is one of:

- `introductory` — directly guided operation;
- `basic` — same idea with a small variation;
- `applied` — known technique in a changed data/context;
- `transfer` — learner must recognize which learned technique applies;
- `challenge` — combines a small number of already-mastered competencies.

Higher difficulty must not mean only more lines, larger inputs, boilerplate, obscure API trivia, or documentation lookup.

## Required metadata for new exercises

The original six starter katas predate this contract and are explicitly grandfathered in `root_kata.catalog.STARTER_PATH_IDS`.

Every new exercise must include a `curriculum` object in `exercise.json`:

```json
{
  "curriculum": {
    "competency": "Choose or diagnose a histogram range by reasoning about underflow and overflow.",
    "prerequisites": ["cpp-root-histogram-inspect"],
    "transfer_level": "applied",
    "misconception": "The visible plotting range contains all filled observations.",
    "observable_success": "The learner detects hidden under/overflow and corrects the representation.",
    "source": {
      "repository": "fbientrigo/root-student-course",
      "path": "course/notebooks/core/01-histograms-and-graphs.ipynb",
      "concept": "underflow, overflow and histogram range"
    }
  }
}
```

`source.ref` may additionally record a commit SHA when useful for exact provenance.

The catalog validates this contract. Unknown prerequisite IDs and unknown transfer levels fail tests.

For planned exercises, copy curriculum meaning from the matching triad CSV row. Do not silently substitute a different competency, role or acceptance condition.

## Source policy

Primary curriculum source:

`fbientrigo/root-student-course`

The source baseline is pinned in `curriculum/plan.json`.

For ROOT behavior, authoritative ROOT documentation outranks inference when the source lesson is ambiguous or version-sensitive.

The source course is primarily Python-oriented. ROOT Kata may teach the same competency in C++/ROOT. Do **not** translate source Python line by line.

Record the source concept that motivated the kata, then implement the smallest exercise that exposes that competency in ROOT Kata's existing engine.

## Candidate quality gate

When a reviewer/design task proposes a syllabus change, reject a candidate when its main difficulty is:

- memorizing syntax;
- copying boilerplate;
- finding an API name in documentation;
- writing more lines without new reasoning;
- accidental C++ complexity;
- repeating an already-covered competency without useful transfer;
- pretending a different input value is a meaningful `limitation` exercise;
- calling an exercise `integration` when it does not require any previously learned idea.

Prefer candidates where a wrong mental model produces visible, interpretable feedback.

Routine implementation workers should not reopen candidate selection for already planned rows.

## Prerequisites

The triad CSV uses stable ROOT Kata exercise IDs in `prerequisites`; multiple IDs are separated by `|`.

Prerequisites must precede the exercise in the ordered curriculum. Keep them minimal: list what the learner genuinely needs, not every earlier exercise.

Do not build a generalized dependency system unless the product later demonstrates a need for one.

## Tests and verification

Every curriculum change must pass the lightweight repository gate:

```bash
python scripts/build_pages.py
python -m unittest discover -s tests -v
```

GitHub CI intentionally does **not** install CERN ROOT.

For a kata whose row has `requires_real_root=true`, the author/agent must additionally run the relevant reference solution and integration tests in a real ROOT Kata environment before changing that row to `implemented` or marking a milestone ready for review.

A passing no-ROOT CI is necessary but not sufficient evidence for new ROOT behavior.

## Autonomous work unit

A recurring worker advances **one exercise row at a time** unless explicitly instructed to take a small coherent batch.

A milestone branch may span many rows and several autonomous runs.

Each routine run should:

1. read `AGENTS.md` and `curriculum/plan.json`;
2. find `current_milestone`;
3. open only `curriculum/triads/<current-milestone>.csv`;
4. scan rows top to bottom and select the first `planned` exercise whose prerequisites are implemented;
5. stop and report evidence if an earlier row is `blocked`;
6. inspect only the source material needed for that row;
7. implement the named `exercise_id` using the existing kata format;
8. preserve the planned `role`, competency and acceptance meaning;
9. run the repository gate;
10. run real-ROOT validation when required;
11. only after verification change that CSV row to `implemented` and commit code plus state change together.

The worker must not change `current_milestone` merely because it finished an exercise or a triad.

When all intended rows in the active milestone are implemented, leave the milestone for independent review. A reviewer may then assess the accumulated learning progression and advance the macro plan deliberately.

Open a PR when the branch reaches a meaningful learner-facing milestone, not because a fixed number of days or source files has elapsed.

## Review gate

Periodic independent review should check:

- coherent progression and prerequisite accuracy;
- whether each `normal` exercise teaches the ordinary operation cleanly;
- whether each `limitation` exposes a real misconception or boundary;
- whether each `integration` meaningfully combines prior knowledge;
- duplicate or cosmetic exercises;
- transfer level correctness;
- ROOT correctness;
- deterministic tests and causal feedback;
- provenance;
- accidental implementation complexity.

A rejection should produce concrete feedback, followed by a bounded repair loop and re-verification.

A reviewer may redesign a weak triad, but should preserve the distinction between evidence-backed syllabus design and routine implementation.

## Non-goals

Curriculum expansion does not justify:

- an LMS;
- accounts;
- a curriculum database;
- cloud execution;
- hidden tests;
- a new frontend framework;
- a new compiler/runtime service;
- agent-specific production runtime code.

Reuse the existing catalog, runner, harness, validator, progress and page-generation paths.
