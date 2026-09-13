# NEXT — one objective for the next session

## Objective

Review the G4 blocker before authorizing another gate. The direct standalone
`TH1D` route requires `TH1D::TH1D(char const*, char const*, int, double, double)`
from Hist, whose declared chain reaches Core and CLING.

## Constraints

- Do not start a Core, MathCore, Hist, Cling, LLVM, or rootcling build without a
  separately approved scope.
- Do not emulate `TH1D` or replace the unresolved constructor.

## Why this is next

G4 supplied the requested evidence; a full Hist/Core route is not a small
follow-up to that falsification gate.
