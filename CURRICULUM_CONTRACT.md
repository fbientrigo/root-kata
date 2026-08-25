# ROOT Kata curriculum contract

This file is the durable contract for adding curriculum, including autonomous agent work.

The implementation should stay small. Curriculum growth must not require new runtime architecture.

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

## Source policy

Primary curriculum source:

`fbientrigo/root-student-course`

For ROOT behavior, authoritative ROOT documentation outranks inference when the source lesson is ambiguous or version-sensitive.

The source course is primarily Python-oriented. ROOT Kata may teach the same competency in C++/ROOT. Do **not** translate source Python line by line.

Record the source concept that motivated the kata, then implement the smallest exercise that exposes that competency in ROOT Kata's existing engine.

## Candidate quality gate

Reject a candidate when its main difficulty is:

- memorizing syntax;
- copying boilerplate;
- finding an API name in documentation;
- writing more lines without new reasoning;
- accidental C++ complexity;
- repeating an already-covered competency without useful transfer.

Prefer candidates where a wrong mental model produces visible, interpretable feedback.

## Prerequisites

`curriculum.prerequisites` contains stable ROOT Kata exercise IDs.

Prerequisites must already exist in the repository. Keep them minimal: list what the learner genuinely needs, not every earlier exercise.

Do not build a generalized dependency system unless the product later demonstrates a need for one.

## Tests and verification

Every curriculum change must pass the lightweight repository gate:

```bash
python scripts/build_pages.py
python -m unittest discover -s tests -v
```

GitHub CI intentionally does **not** install CERN ROOT.

For a kata whose behavior depends on ROOT, the author/agent must additionally run the relevant reference solution and integration tests in a real ROOT Kata environment before marking a milestone ready for review.

A passing no-ROOT CI is necessary but not sufficient evidence for new ROOT behavior.

## Autonomous work unit

A recurring worker should advance **one coherent slice of the current curriculum milestone per run**.

A milestone branch may span several related source lessons/classes. Do not force one notebook or one daily run into its own PR.

Each run should:

1. inspect the current branch and this contract;
2. inspect the relevant source material;
3. identify the next observable competency;
4. reject weak candidate exercises before coding;
5. implement a small coherent batch using the existing kata format;
6. run the repository gate;
7. run real-ROOT validation when required and available;
8. commit a concise handoff/state for the next run.

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
