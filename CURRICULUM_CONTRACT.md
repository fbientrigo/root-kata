# ROOT Kata curriculum contract

This file is the durable contract for adding curriculum, including autonomous agent work.

The implementation should stay small. Curriculum growth must not require new runtime architecture.

## Authoritative syllabus

`curriculum/plan.json` is the authoritative ordered syllabus and implementation queue.

Routine autonomous workers **execute the plan; they do not redesign it**.

A routine worker must not invent a new topic, reorder units, broaden a competency, change transfer level, or skip a blocked earlier unit merely because another exercise looks easier to implement. Syllabus changes require a deliberate reviewer/design task with evidence.

`AGENTS.md` is the short operational entry point for future agents.

## Learning model

Use source courses as evidence of **competencies**, not as files to split mechanically.

```text
source lesson
→ observable competency
→ small learning experience
→ kata
→ transfer kata
```

Prefer, when useful:

**Manipulate → Observe → Predict → Code**

A kata should normally teach or test one causal idea and take roughly 5–15 minutes.

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
    "competency": "Create and inspect a histogram for a changed measurement sample.",
    "prerequisites": ["cpp-root-histogram"],
    "transfer_level": "applied",
    "misconception": "The learner copies a familiar binning without checking whether it represents the new data.",
    "observable_success": "The implementation constructs the requested histogram and the visible tests confirm its binning and contents.",
    "source": {
      "repository": "fbientrigo/root-student-course",
      "path": "course/notebooks/core/01-histograms-and-graphs.ipynb",
      "concept": "histogram construction and inspection"
    }
  }
}
```

`source.ref` may additionally record a commit SHA when useful for exact provenance.

The catalog validates this contract. Unknown prerequisite IDs and unknown transfer levels fail tests.

For planned exercises, copy curriculum meaning from the matching unit in `curriculum/plan.json`; do not silently substitute a different competency.

## Source policy

Primary curriculum source:

`fbientrigo/root-student-course`

The current syllabus was distilled from the source course baseline recorded in `curriculum/plan.json`.

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
- repeating an already-covered competency without useful transfer.

Prefer candidates where a wrong mental model produces visible, interpretable feedback.

Routine implementation workers should not reopen this candidate-selection process for already planned units.

## Prerequisites

`curriculum.prerequisites` contains stable ROOT Kata exercise IDs.

Prerequisites must already exist in the repository when the exercise is published. Keep them minimal: list what the learner genuinely needs, not every earlier exercise.

`curriculum/plan.json` may reference target exercise IDs from earlier planned units because those units are expected to be implemented first. This is why the plan is strictly ordered.

Do not build a generalized dependency system unless the product later demonstrates a need for one.

## Tests and verification

Every curriculum change must pass the lightweight repository gate:

```bash
python scripts/build_pages.py
python -m unittest discover -s tests -v
```

GitHub CI intentionally does **not** install CERN ROOT.

For a kata whose behavior depends on ROOT, the author/agent must additionally run the relevant reference solution and integration tests in a real ROOT Kata environment before marking the corresponding plan unit `implemented` or marking a milestone ready for review.

A passing no-ROOT CI is necessary but not sufficient evidence for new ROOT behavior.

## Autonomous work unit

A recurring worker should advance **one planned unit of the current curriculum milestone per run**, unless that unit explicitly names a small batch of target exercises.

A milestone branch may span several related source lessons/classes and many autonomous runs. Do not force one notebook or one daily run into its own PR.

Each routine run should:

1. read `AGENTS.md` and `curriculum/plan.json`;
2. find `current_milestone`;
3. select the first `planned` unit in listed order whose prerequisites are already implemented;
4. stop and report evidence if an earlier unit is `blocked`;
5. inspect only the source material needed for that planned unit;
6. implement the unit's named `target_exercises` using the existing kata format;
7. run the repository gate;
8. run real-ROOT validation when `requires_real_root` is true;
9. only after verification, mark that unit `implemented` in `curriculum/plan.json` and commit code plus state change together.

The worker must not change `current_milestone` merely because it finished one unit.

When all intended units in the active milestone are implemented, leave the milestone for independent review. A reviewer may then move the milestone to `review`, approve/fix the accumulated work, and advance the plan deliberately.

Open a PR when the branch reaches a meaningful learner-facing milestone, not because a fixed number of days or source files has elapsed.

## Review gate

Periodic independent review should check:

- coherent progression;
- duplicate or trivial exercises;
- transfer level correctness;
- ROOT correctness;
- prerequisite accuracy;
- visible tests and causal feedback;
- provenance;
- accidental implementation complexity.

A rejection should produce concrete feedback, followed by a bounded repair loop and re-verification.

A reviewer may propose edits to `curriculum/plan.json`, but should preserve the distinction between evidence-backed syllabus design and routine implementation.

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
