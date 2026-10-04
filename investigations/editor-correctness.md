# Editor correctness investigation

Baseline: `main`, `4e9e0ed227206fd008ef9316f518277b2e0c1a33` (PR #29).
Browser experiments: Chrome Headless Shell 154.0.8037.97, Linux.

## 1. Root cause

**Verified and reproduced:** the textarea is authoritative, but its visible
Prism projection is updated only on `input`, asynchronously in an animation
frame. Both indentation branches use `setRangeText()` without emitting `input`.
The native text changes while the transparent textarea hides those changes.
The Prism text can remain obsolete indefinitely until another input arrives.

**Reproduced visual consequence:** Chromium paints selected textarea glyphs
in its selection foreground color even though the unselected text is transparent.
Those glyphs overlap the old Prism glyphs at different positions after Tab.
The normally visible Prism text is deliberately non-interactive (`pointer-events:
none`, `aria-hidden`); caret and selection belong to the other layer.

**Independent reproduced failure:** a textarea preserves the empty final line
after a terminal newline; the original pre does not. Equal strings therefore do
not imply equal scroll ranges. At the bottom of an 80-line source, measured
textarea/pre scroll heights were 1880/1857 px and scroll offsets 1441/1418 px.
Matching font and line-height declarations do not fix this clamp.

## 2. State machine and authority

| Stage / operation | Original behavior | Authority / boundary |
| --- | --- | --- |
| Initial HTML | Visible native textarea; empty hidden pre | Textarea value |
| Deferred scripts | Prism core, clike, c, cpp, site, highlighter in that order | No worker or network grammar loading |
| Activation | Synchronous highlight, scroll copy while pre hidden, then transparent textarea | Textarea value; pre becomes visible projection |
| Prism DOMContentLoaded | Core also automatically highlights matching code nodes | A second renderer, using code-node text, not textarea value |
| Typing, paste, delete, undo, redo | Native mutation emits input; render scheduled for a later frame | Textarea changes immediately |
| Tab, Shift+Tab | Native mutation via setRangeText; no input notification | Textarea changes; projection remains old |
| `.value = ...` | No automatic input event | Caller must notify after mutation; repository test submit helper already does |
| `setRangeText(...)` | No automatic input event; selection is updated natively | Both repository indentation branches omitted notification |
| Scroll | Copies textarea offsets into independently clamped pre offsets | Native textarea scroll is authoritative |
| Selection | Browser paints textarea selection over Prism | Textarea selectionStart/End |
| Resize | CSS shares size, padding, font and unwrapped whitespace; native scroll can clamp | Scroll listener handles subsequent native scroll changes |
| Run / native | Reads textarea.value into POST body | Never reads Prism |
| Run / WASM | Awaits module import, then reads textarea.value | Additional race: source can change after Run was clicked |

The last WASM race was independently reproduced by holding the module response,
clicking Run, editing from source A to B, and releasing the import. The old runner
received B. The fix snapshots source at submission, before this await.
Editing during an already submitted run remains possible; that run deliberately
uses its submitted snapshot, not later edits.

## 3. Deterministic reproduction and evidence

1. Open `/solve/cpp-root-histogram.html`.
2. Put the caret before `return nullptr;` and press Tab.
3. Read value, highlight.textContent, selectionStart/End and both scroll offsets.
   The textarea has two additional spaces; Prism does not.
4. Select the changed line: selected native glyphs overlap obsolete highlighted
   glyphs. Browser screenshot inspection confirmed the duplication.
5. Run without typing again. A spy at the real `ExerciseRunner.runExercise`
   module boundary receives the changed textarea source, not the visible source.

This is not limited to cosmetically different whitespace. With:

```cpp
const char* answer() { return R"(first
second)"; }
```

select `second` and press Tab. The original editor still displays `second`,
but the submitted raw string contains `  second`, changing its value.

Additional experiments:

| Candidate | Trigger and expected state | Result / relation to observations |
| --- | --- | --- |
| Content desynchronization | Tab, then select/Run; different strings | Reproduced persistently; explains overlapping selected text |
| Frame scheduling | Hold requestAnimationFrame, perform native input; different strings until release | Reproduced; demonstrates deferred consistency, not proof of a missed normal paint |
| Selection painting | Select stale transparent textarea | Reproduced; makes hidden authoritative text visible over stale glyphs |
| Scroll mismatch | Long source ending in newline, scroll to bottom | Reproduced with equal strings; roughly one-line vertical displacement |
| Geometry/font mismatch | Compare computed font, padding, line-height and unwrapped text | Tested default metrics match; no independent font mismatch established |
| Silent programmatic writes | Assign value or call setRangeText without input | Reproduced; current application producers are the two indentation branches |
| Prism normalization | Insert NBSP and render | Reproduced: Prism turns U+00A0 into U+0020, leaving different strings even after render |
| Stale/failed Prism | Throw during highlight after activation | Original code leaves stale projection; injected failure now reveals native editor |
| Initialization ordering | Deferred ordered loading and automatic Prism pass | Two writers verified; not established as the user's screenshot cause |
| Browser compositing defect | Transient GPU/platform paint failure | Not established; content and geometry failures suffice without this hypothesis |

**Inference:** normalization after a subsequent input fits the reported spontaneous
recovery. Selection alone does not refresh the old projection. The actual user's
screenshots were not supplied with this task, so their exact trigger remains unknown.

## 4. Severity

Yes: the original application can show source A while submitting source B,
including semantically different raw-string content. Run always uses the textarea;
the bug is a misleading visible projection, not compilation of Prism HTML.
This is a learner correctness defect and should block acceptance of this editor.

The boundary spy proves the source handed to execution. It does not claim to have
compiled ROOT code in this environment.

## 5. Smallest viable correction implemented

- Render synchronously on input and explicitly emit input after each application
  indentation mutation. No frame queue, polling, observer or new dependency.
- Translate the code layer by the textarea's exact native scroll offsets instead
  of asking the pre to scroll beyond its own maximum. Native scrolling, empty
  final lines and scrollbar space remain owned by the textarea.
- Give the code node a block box so the translation applies.
- Specify transparent selected textarea glyphs and a translucent visible selection
  background. Only Prism paints code glyphs in overlay mode. Forced colors uses
  native CanvasText/HighlightText/Highlight instead.
- Activate the overlay only when Prism text matches the textarea exactly. On
  normalization or exceptions, reveal the native textarea; later inputs can recover.
- Set Prism `data-manual` so the editor has one projection writer.
- Snapshot the submitted source before importing the WASM runner.

Direct silent writes from arbitrary external scripts remain outside the editing
contract: value and setRangeText do not emit input, and MutationObserver cannot
observe these property changes. All current ROOT Kata editing producers are
covered. Future programmatic edits must emit input in the same task. Native API
monkey-patching would add complexity to cover callers the application does not have.

## 6. Alternatives considered

| Alternative | Why weaker |
| --- | --- |
| Notify only after Tab | Fixes the persistent case, leaves deferred input, scroll clamp and selection overlap |
| Refresh only before Run | Execution might match after clicking, but the learner still edits misleading code |
| Add keyup/change/selectionchange listeners | Indirect synchronization misses silent writes and retains timing gaps |
| Poll / observe DOM mutations | Polling leaves gaps; DOM mutation observers do not see textarea value changes |
| Append a space to highlight text | Changes the source projection; historical commit 3263a5b already removed this approach |
| Add a final-line pseudo-element | Repairs that scroll height but still couples two independent scrollports and scrollbar geometry |
| Hide native selection text without synchronization | Conceals evidence of stale content rather than correcting it |
| Remove syntax highlighting | Strong correctness fallback, but unnecessary loss of useful learning feedback |
| Replace textarea with contenteditable/editor framework | Recreates native editing/accessibility/mobile behavior; evidence does not justify it |

## 7. Regression coverage and validation

The existing dependency-free CDP browser harness now checks:

- initial readiness with animation frames held from before page loading;
- native insertion and clipboard paste; delete, effective undo and redo;
- caret and block Tab/Shift+Tab, including raw-string content;
- programmatic value/replacement followed by the application's input notification;
- immediate source equality inside the same task, before any frame convergence;
- native selection ranges, decorative-layer semantics and selected text painting;
- both scroll axes, terminal newline, native wheel events and mobile viewport;
- forced colors, Prism normalization, injected failure and recovery;
- Run's submitted source across a deliberately delayed module import and later edit.

The suite fails on the original highlighter with `native typing: stale source` and
passes after the correction while animation frames remain held. Tests disable
HTTP cache to prevent restored baseline assets surviving in the reused profile.
Waiting for module completion or a native scroll event does not replace same-task
content assertions or release held highlight frames.

Run the editor suite without rebuilding ROOT:

```bash
ROOT_KATA_EDITOR_ONLY=1 CHROMIUM_BIN=/path/to/chromium node tests/test_browser_product.mjs
```

Validation: editor browser suite passed; static build passed; Python suite ran
121 tests successfully, with 3 real-ROOT tests skipped because ROOT is unavailable.
Full browser acceptance passed the editor section and dashboard, then failed at
the first compiler execution with `status-request_error`: `docs/wasm` runtime
artifacts are absent. Its 12 real-WASM execution cases remain unvalidated here.
The WASM workflow now watches `docs/editor_highlight.js` as well.

Remaining uncertainty: Firefox/WebKit, physical mobile devices, IME-specific paint
behavior, and the user's exact original screenshot trigger were not tested.
