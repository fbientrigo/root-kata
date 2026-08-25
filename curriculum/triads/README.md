# Curriculum learning triads

This directory enriches the macro syllabus in `curriculum/plan.json` with the exact exercise-level progression used by routine curriculum workers.

## Default pattern

A high-value ROOT topic should normally be learned through three different encounters:

1. **normal** — use the concept successfully in its ordinary form;
2. **limitation** — meet a boundary, misleading assumption, failure mode, or semantic trap that reveals where the ordinary pattern breaks;
3. **integration** — use the same concept together with something already learned in a small realistic analysis task.

This is a learning progression, not a quota. Do not manufacture three nearly identical exercises. A reviewer may merge or redesign a weak triad, but routine workers execute the planned rows.

The intended cognitive movement is:

```text
use it
  ↓
see where it breaks
  ↓
use it with something else
```

This complements the product teaching loop:

**Manipulate → Observe → Predict → Code**

The limitation exercise should expose a causal misconception whenever possible. The integration exercise should increase transfer distance, not merely code length.

## Files

Each active/core milestone has one CSV file:

- `m1-histograms-modeling.csv`
- `m2-files-datasets.csv`
- `m3-rdataframe-essentials.csv`
- `m4-rvec-object-selection.csv`
- `m5-analysis-workflows.csv`
- `m6-analysis-transfer.csv`

The CSV is deliberately simple and stdlib-readable. `|` separates multiple prerequisite exercise IDs.

`curriculum/plan.json` remains the macro syllabus: milestone order, source-course baseline and broad curriculum architecture.

The matching triad CSV is the **exercise-level implementation queue** for that milestone.

## Routine worker selection

1. Read `curriculum/plan.json` and find `current_milestone`.
2. Open only the matching CSV in this directory.
3. Scan rows top to bottom.
4. The first `planned` row whose prerequisites are implemented is the next exercise.
5. If an earlier row is `blocked`, stop and report evidence; do not skip it.
6. Implement exactly that row's competency and acceptance contract.
7. Run lightweight tests and real-ROOT validation when required.
8. Only after verification change that row to `implemented` in the CSV and commit code plus status together.

Do not redesign the triad during a routine run.

## Current scope

The core queue contains 17 themes and 51 planned exercise encounters across histogram/model literacy, files/TTree, RDataFrame, RVec object selections, reusable workflows and independent analysis transfer.

Python UHI, NumPy interoperability and distributed RDataFrame remain deferred in `curriculum/plan.json`; this enrichment does not silently pull them into the core path.
