# ROOT Kata — agent context

This file is the short operational entry point for future coding and curriculum agents.

## Read in this order

For routine curriculum work, read only what you need:

1. `AGENTS.md` — product and execution constraints.
2. `curriculum/plan.json` — **authoritative syllabus and next work item**.
3. `CURRICULUM_CONTRACT.md` — authoring and pedagogy rules.
4. The files for the exercise/engine area you are changing.

Do not re-read the whole repository or redesign the course before implementing a planned unit.

## Product mission

ROOT Kata is a small interactive learning environment for physics students and early HEP learners who may know basic programming but do not yet have a reliable mental model of ROOT analyses.

The learner should progress toward independent use of real CERN ROOT. ROOT Kata is a bridge to ROOT, not a replacement reference manual.

The implementation should stay austere and portable. The learning experience may be visual, tactile and interactive when that makes cause and effect clearer.

Teaching default:

**Manipulate → Observe → Predict → Code**

A learner should frequently have to decide, inspect, predict, compare or explain. Do not turn a planned kata into API trivia.

## Current architecture

Exercises live under:

`src/root_kata/exercises/<exercise-id>/`

A normal C++ kata uses:

- `exercise.json` — metadata and curriculum provenance;
- `solution.cpp` — learner starter;
- `harness.cpp` — observable execution probes;
- `validator.py` — visible semantic expectations;
- optional `problem.md` and preview artifacts.

Execution is local:

learner C++ + harness → g++/clang++ + `root-config` when needed → executable → structured results → validator → visible feedback.

There is no cloud runner, account system, hidden-test service or hostile-code sandbox.

Local progress is stored in `~/.root-kata/progress.json`. Stable exercise and badge IDs are part of the product contract.

## Source hierarchy

For curriculum meaning:

1. `curriculum/plan.json` decides **what to implement and in what order**.
2. `CURRICULUM_CONTRACT.md` decides **how a good kata is designed**.
3. `fbientrigo/root-student-course` is the primary source-course evidence.
4. Authoritative ROOT documentation decides ROOT behavior when facts are uncertain or version-sensitive.

The source course is largely Python-oriented. ROOT Kata's current core is C++/ROOT. Extract the competency; do not translate notebook code line by line.

## Routine autonomous curriculum worker

A routine recurring worker is an **executor, not a syllabus designer**.

Algorithm:

1. Read `curriculum/plan.json`.
2. Find `current_milestone`.
3. In listed order, select the first unit with `status: "planned"` whose prerequisites are already implemented.
4. If an earlier unit is `blocked`, do not skip it. Report the blocker and stop.
5. Implement exactly the unit's `target_exercises` and stated competency. Small implementation choices are yours; curriculum scope is not.
6. Reuse the existing catalog, runner, harness, validator, localization, progress and page-generation patterns.
7. Run the lightweight repository gate:

   ```bash
   python scripts/build_pages.py
   python -m unittest discover -s tests -v
   ```

8. If the unit has `requires_real_root: true`, also run its reference solution/integration path in an environment with CERN ROOT before marking it implemented.
9. Only after verification, change that unit's status from `planned` to `implemented` in `curriculum/plan.json` and commit the implementation plus status change together.
10. Leave the branch in a reproducible state for the next run.

Do **not** invent new syllabus items, reorder milestones, broaden target competencies or change transfer levels during a routine run. If the plan appears wrong, leave evidence for the reviewer instead.

## Branch and PR lifecycle

Use a curriculum branch for the active milestone, conceptually:

`curriculum/<milestone-id>`

Several autonomous runs may accumulate on that branch.

A milestone is not a PR merely because a day or notebook ended. When all intended units are implemented and coherent, move the milestone to review and request independent review. Open/merge a PR at a meaningful learner-facing milestone.

## Reviewer role

A reviewer may challenge the plan when evidence warrants it. Check:

- progression and prerequisite accuracy;
- duplicated/trivial exercises;
- transfer level;
- ROOT correctness;
- deterministic tests and causal feedback;
- provenance;
- accidental C++ or infrastructure complexity.

A syllabus change is a deliberate review/design action, not something the daily implementation worker does opportunistically.

## Verification boundary

GitHub CI intentionally does **not** install CERN ROOT. It validates the portable Python/catalog/page/test layer.

A green GitHub CI is necessary but not sufficient evidence for a new ROOT-dependent kata. Real-ROOT verification belongs in the development environment before milestone review.

Do not add ROOT to CI merely to make this distinction disappear.

## Engineering constraints

Prefer, in order:

1. no new code if unnecessary;
2. existing repository code;
3. Python/C++/browser/Jupyter platform capabilities;
4. existing dependencies;
5. the smallest justified new dependency only as a last resort.

Do not add architecture for hypothetical future lessons.

Accessibility, scientific correctness, data integrity and clear learner feedback are not optional simplifications.

## Out of scope unless explicitly requested

Do not turn curriculum work into:

- an LMS;
- accounts or leaderboards;
- remote/cloud execution;
- hidden tests;
- a generic online IDE;
- distributed analysis infrastructure;
- a frontend-framework migration;
- a generalized curriculum database or agent runtime.

The best routine change is usually one polished vertical learning slice that passes the existing engine and leaves the next slice obvious.
