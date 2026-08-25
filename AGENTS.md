# ROOT Kata — agent context

This file is the short operational entry point for future coding and curriculum agents.

## Read in this order

For routine curriculum work, read only what you need:

1. `AGENTS.md` — product and execution constraints.
2. `curriculum/plan.json` — macro syllabus and `current_milestone`.
3. `curriculum/triads/<current-milestone>.csv` — **authoritative exercise-level queue**.
4. `CURRICULUM_CONTRACT.md` — authoring and pedagogy rules.
5. The files for the exercise/engine area you are changing.

Do not re-read the whole repository or redesign the course before implementing the next planned exercise.

## Product mission

ROOT Kata is a small interactive learning environment for physics students and early HEP learners who may know basic programming but do not yet have a reliable mental model of ROOT analyses.

The learner should progress toward independent use of real CERN ROOT. ROOT Kata is a bridge to ROOT, not a replacement reference manual.

The implementation should stay austere and portable. The learning experience may be visual, tactile and interactive when that makes cause and effect clearer.

Teaching default:

**Manipulate → Observe → Predict → Code**

A learner should frequently have to decide, inspect, predict, compare or explain. Do not turn a planned kata into API trivia.

## Curriculum shape: use → limitation → integration

High-value concepts are normally revisited as a learning triad:

1. `normal` — ordinary useful use;
2. `limitation` — a boundary, semantic trap, failure mode or misleading assumption;
3. `integration` — the concept combined with something already learned in a practical analysis task.

The goal is not three similar exercises. The learner should first make the tool work, then understand where the naive mental model breaks, then transfer the idea into a richer context.

The exact triads are already planned in `curriculum/triads/`. Routine workers do not invent them.

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

1. `curriculum/plan.json` decides milestone order and current milestone.
2. The matching `curriculum/triads/*.csv` decides the exact next exercise, role, competency and acceptance evidence.
3. `CURRICULUM_CONTRACT.md` decides how a good kata is implemented.
4. `fbientrigo/root-student-course` is the primary source-course evidence.
5. Authoritative ROOT documentation decides ROOT behavior when facts are uncertain or version-sensitive.

The source course is largely Python-oriented. ROOT Kata's current core is C++/ROOT. Extract the competency; do not translate notebook code line by line.

## Routine autonomous curriculum worker

A recurring worker is an **executor, not a syllabus designer**.

Algorithm:

1. Read `curriculum/plan.json` and find `current_milestone`.
2. Open only `curriculum/triads/<current-milestone>.csv`.
3. Scan rows from top to bottom.
4. Select the first row with `status=planned` whose `prerequisites` are already implemented.
5. If an earlier row is `blocked`, do not skip it. Report the blocker and stop.
6. Implement exactly that row's `exercise_id`, `competency`, learning `role` and `acceptance` contract.
7. Reuse the existing catalog, runner, harness, validator, localization, progress and page-generation patterns.
8. Run the lightweight repository gate:

   ```bash
   python scripts/build_pages.py
   python -m unittest discover -s tests -v
   ```

9. If `requires_real_root=true`, also run the reference solution/integration path in an environment with CERN ROOT.
10. Only after verification change that CSV row from `planned` to `implemented` and commit the exercise plus state change together.
11. Leave the branch reproducible for the next run.

Do **not** invent syllabus items, reorder themes, change `normal/limitation/integration`, broaden competencies or substitute a different exercise during a routine run. If the plan appears wrong, leave evidence for the reviewer.

## What each learning role must feel like

### normal

The learner should successfully perform the common operation and observe its direct effect. Keep accidental difficulty low.

### limitation

Do not make this merely a harder input. Expose a real boundary or misconception: under/overflow, wrong key, missing branch, cut boundary, eager execution, object-mask mismatch, output schema, model mismatch, unsafe shared state, etc.

The learner should be able to answer **why** the ordinary approach failed.

### integration

Combine the concept with an already-mastered idea: selection + histogram, TTree + RDataFrame, mask + derived pT + histogram, Snapshot + reopen + second analysis, cutflow + distribution, helper + MT pipeline, or two-sample comparison.

Increase transfer distance, not boilerplate.

## Branch and PR lifecycle

Use a curriculum branch for the active milestone, conceptually:

`curriculum/<milestone-id>`

Several autonomous runs may accumulate on that branch. A milestone is not a PR merely because a day or source notebook ended.

When all intended rows for the active milestone are implemented and coherent, leave the milestone for independent review. Open/merge a PR at a meaningful learner-facing milestone.

## Reviewer role

A reviewer may challenge the plan when evidence warrants it. Check:

- progression and prerequisite accuracy;
- whether each triad actually changes the learner's mental model;
- duplicated or cosmetic exercises;
- transfer distance;
- ROOT correctness;
- deterministic tests and causal feedback;
- provenance;
- accidental C++ or infrastructure complexity.

A weak triad may be merged or redesigned by a deliberate reviewer/design task. Routine workers do not do that opportunistically.

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
