# Architecture Decisions — ROOT WebAssembly

## 2026-09-18: Decorative Graphics and Canvas Outputs in WebAssembly

### Context
In native ROOT Kata execution, some exercises (such as `cpp-root-histogram`) instantiate `TCanvas` and invoke `c.SaveAs("preview.png")` in their evaluation harnesses to produce a decorative preview plot.

In the WebAssembly browser environment:
1. Validating learner submissions is 100% semantic and numeric: validators check histogram entries, bin contents, integrals, means, standard deviations, and formula evaluations. No automated validator checks image pixels or PNG files.
2. Linking ROOT graphics subsystems (`libGpad`, `libGraf`, X11/Cocoa/browser-canvas graphics devices, font rendering engines) incurs substantial payload size, complex platform bindings, and additional runtime failure surfaces.
3. Attempting to draw to `TCanvas` in WebAssembly triggers internal reflection (`TClass::Init` -> `SetClassInfo`) before graphics symbols are even invoked.

### Decision
1. **Decorative graphics are excluded from the core WebAssembly subset.**
   - We do not port or bundle `libGpad` / `libGraf` into the lean browser runtime.
   - For in-browser execution, decorative canvas draws are bypassed or replaced with lightweight ASCII / text summaries (e.g. `[h_pt] 10 bins [0, 100], entries=8`).
2. **Local ROOT for Image Generation:**
   - If a student wishes to generate and inspect actual PNG/PDF plots or interact with full graphical canvases, they can use the UI's runtime selector to target their own local/server ROOT instance.
3. **Keep the Browser Engine Focused on Physics Computation:**
   - The browser WebAssembly runtime focuses strictly on physics computations, data structures (`TH1D`, `TAxis`, `TGraph`), formula evaluation (`TF1`, `TFormula`), and grading contracts.
