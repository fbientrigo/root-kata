# Exercise format v0.2

```
exercises/<id>/
├── exercise.json
├── solution.cpp
├── harness.cpp
├── validator.py
├── problem.md
└── data/
```

Each public kata is described by `exercise.json`; C++ exercises compile the student's `solution.cpp` together with a visible `harness.cpp`, then `validator.py` converts emitted values into named PASS/FAIL cases.

Useful public metadata: `difficulty`, `order`, `published`, `estimated_minutes`, `topics`, `learning_goal`, `resources`, and `problem_markdown`.

`requires: ["ROOT"]` makes the runner use `root-config --cflags --libs`; leave it empty for plain C++.

Before shipping a kata:
1. The starter compiles and fails tests meaningfully.
2. A reference solution reaches n/n.
3. Test names read like requirements.
4. Regenerate the static site with `python scripts/build_pages.py`.

Authoring skeletons live in `docs/templates/problem.md` and `docs/templates/problem.adoc`.
