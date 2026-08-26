"""Manual ES/EN localization. Stable internal ids never depend on language.

Resolution order for the active language:
    $ROOT_KATA_LANG  >  ~/.root-kata/config.json  >  default (es)

All student-facing strings live in _STRINGS below; exercise-specific copy
lives next to each exercise in its own `exercise.json`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

LANGS = ("es", "en")
DEFAULT_LANG = "es"

_STRINGS: dict[str, dict[str, str]] = {
    # ---------------------------------------------------------------- Spanish
    "es": {
        # generic labels
        "difficulty.introductory": "Introductorio",
        "difficulty.easy": "Fácil",
        "difficulty.intermediate": "Intermedio",
        "difficulty.hard": "Difícil",
        "kind.cpp": "C++",
        "kind.python": "Python",
        "minutes_estimate": "≈{n} min",
        # statement card
        "must_handle": "Requisitos",
        "example": "Ejemplo",
        "input_label": "entrada",
        "output_label": "salida",
        "references": "Referencias",
        "badge_on_completion": "Insignia al resolver",
        "badge_line": "🏅 Insignia al resolver: {badge}",
        "edit_cell_below": "Edita la celda de abajo y ejecútala con {key1}+{key2}. Tu código se guarda automáticamente.",
        "edit_file_then_check": "Edita {path}, luego ejecuta {cmd}.",
        "start_here": "Empieza aquí: {cmd}",
        "statement_edit_line": "  Editar: {path}",
        "statement_then_line": "  Después: rk.check('{exercise_id}')",
        # result card
        "status.passed": "Resuelto",
        "status.failed": "Aún no",
        "status.compile_error": "Error de compilación",
        "status.runtime_error": "Error de ejecución",
        "status.solution_error": "Error en tu código",
        "status.timeout": "Tiempo agotado",
        "status.check_result": "Resultado",
        "next.passed": "Todas las pruebas visibles pasan.\nTu solución quedó guardada localmente.",
        "next.failed": "Empieza por la primera prueba que falla: compara lo que esperaba con lo que produjo tu código.",
        "next.compile_error": "Corrige el primer error del compilador que aparece abajo y vuelve a ejecutar la celda.",
        "next.runtime_error": "Usa el mensaje de ejecución de abajo para identificar dónde se detuvo todo.",
        "next.solution_error": "Corrige el primer error de tu código y vuelve a ejecutar la celda.",
        "next.timeout": "Busca un bucle u operación que nunca termina.",
        "next.default": "Revisa los detalles de abajo y vuelve a ejecutar la celda.",
        "harness_signature_note": "Lo reportó el banco de pruebas: revisa que la firma de tu función coincida exactamente con la del enunciado.",
        "expected_got": "Se esperaba <code>{expected}</code>; se obtuvo <code>{actual}</code>.",
        "tests_label": "Pruebas",
        "preview_alt_default": "Histograma generado por tu código",
        "your_output": "Tu salida",
        "reproduce_outside_jupyter": "Reproducir fuera de Jupyter",
        "logs_line": "Registros: {build} · {run}",
        "need_hint": "¿Necesitas una pista?",
        "new_badge": "Nueva insignia:",
        "continue": "Continuar →",
        "continue_help": "Tu progreso también se reflejará en la web local del catálogo.",
        # plain-text result formatter
        "harness_signature_note_text": "(el error está en el banco de pruebas: normalmente la firma de tu función difiere de la pedida)",
        "stderr_tail": "stderr (final):",
        "preview_saved_text": "  vista previa: {path}",
        "logs_reproduce_text": "  registros: {work}/build.log, run.log   ·   reproducir: sh {work}/compile.sh",
        "expected_got_text": "   esperaba {expected}, obtuvo {actual}",
        # notebook API
        "no_solution_yet": "Aún no hay solución. Ejecuta primero rk.start('{exercise_id}') (crea {path}).",
        "keeping_existing": "(conservando tu {path} actual)",
        "created_path": "Creado {path}",
        "no_hints": "Este ejercicio no tiene pistas.",
        "hint_n": "pista {i}/{n}: {hint}",
        "magic_usage": "uso: %%kata <id-de-ejercicio>",
        "magic_loaded": "root_kata cargado: usa %%kata <id-de-ejercicio> al inicio de una celda.",
        # progress
        "progress_solved": "Resueltos {n}/{m}",
        "attempts_count": "({n} intentos)",
        "badges_prefix": "Insignias:",
        "badges_none": "ninguna aún",
        # badges
        "badge.first_kata.name": "Primer kata",
        "badge.first_kata.desc": "Resuelve cualquier ejercicio",
        "badge.first_root_histogram.name": "Primer histograma ROOT",
        "badge.first_root_histogram.desc": "Llena tu primer TH1D",
        "badge.basics_complete.name": "Fundamentos completados",
        "badge.basics_complete.desc": "Resuelve todos los katas disponibles",
        # runner summaries
        "sum.no_compiler": "No se encontró compilador de C++ (se probó $CXX, g++, clang++). Instala uno y vuelve a ejecutar doctor().",
        "sum.no_root_config": "root-config no está en el PATH. Carga ROOT (p. ej. `source /ruta/a/root/bin/thisroot.sh`) antes de abrir Jupyter.",
        "sum.compile_timeout": "El compilador no terminó en {seconds} s",
        "sum.compile_failed": "Fallo de compilación",
        "sum.compile_failed_at": "Fallo de compilación en {where}: {msg}",
        "sum.run_timeout": "Tu programa tardó más de {seconds} s (¿bucle infinito?)",
        "sum.crashed_signal": "Tu programa falló: {signal}",
        "sum.crashed_exit": "Tu programa falló: código de salida {code}",
        "sum.segv_hint": " (fallo de segmentación: probablemente un índice fuera de rango, un puntero nulo o un histograma sin inicializar)",
        "sum.harness_no_json": "El banco de pruebas no produjo JSON en su última línea de salida. Revisa run.log (¿imprimiste algo después de rk::done()?).",
        "sum.tests_passed": "{n}/{m} pruebas superadas",
        "sum.missing_req": "Falta un requisito en este entorno: {names}",
        "sum.exec_timeout": "La ejecución superó {seconds} s",
        "sum.grader_failed": "El evaluador interno falló",
        "sum.grader_bad_output": "El evaluador interno devolvió una salida inválida",
        # validation defaults
        "val.values_differ": "Los valores difieren",
        "val.not_close": "Los valores no coinciden",
        "val.case_passed": "Superada",
        # lab / CLI
        "lab_prepared": "cuaderno listo: {path}",
        "lab_url": "Jupyter de ROOT Kata: {url}",
        "lab_stop_hint": "Abre esa URL en tu navegador. Pulsa Ctrl-C aquí para detener.",
        "config_current": "Idioma actual: {lang}",
        "config_set": "Idioma cambiado a: {lang}",
        "config_invalid": "Idioma no soportado: {lang} (usa: es, en)",
        # doctor
        "label.python": "Python",
        "label.notebook": "Cuaderno",
        "label.package": "Paquete",
        "label.entry_point": "Punto de entrada",
        "label.jupyter": "Jupyter",
        "label.compiler": "Compilador",
        "label.root": "ROOT",
        "label.root_build": "Compilación ROOT",
        "label.pyroot": "PyROOT",
        "label.workspace": "Espacio de trabajo",
        "label.exercises": "Ejercicios",
        "doc.entry_point_ok": "coincide con este entorno",
        "doc.entry_point_missing": "el comando root-kata no está en el PATH",
        "doc.fix_reinstall": "activa el entorno conda y reinstala con su propio `python -m pip install -e .`",
        "doc.fix_foreign": "elimina la copia ajena (p. ej. `python -m pip uninstall root-kata` fuera de conda) y reinstala dentro del entorno root-kata",
        "doc.package_missing": "no se puede importar ({exc})",
        "doc.fix_package": "ejecuta `{python} -m pip install -e .` dentro de este entorno",
        "doc.jupyter_missing": "jupyterlab no está disponible — `root-kata lab` lo necesita",
        "doc.compiler_missing": "no se encontró g++/clang++",
        "doc.fix_compiler": "instala un compilador de C++ en este entorno",
        "doc.root_found": "root-config encontrado, ROOT {version} en {path}",
        "doc.root_missing": "root-config no está en el PATH — los katas ROOT quedan desactivados",
        "doc.fix_root": "activa el entorno conda root-kata antes de lanzar Jupyter",
        "doc.root_build_fail": "un programa trivial de ROOT no compila",
        "doc.fix_same_env": "revisa que el compilador y ROOT vengan del mismo entorno",
        "doc.root_build_ok": "compila y corre",
        "doc.root_build_runtime_fail": "compila pero falla al correr",
        "doc.pyroot_ok": "importable",
        "doc.pyroot_missing": "no disponible (los warm-ups C++ siguen funcionando)",
        "doc.workspace": "soluciones en ./{kata_dir}/<id>/ · registros en ./.root-kata/<id>/ · progreso en {home}",
        "doc.exercises": "{n} disponibles",
        "doc.fix_exercises": "reinstala el paquete",
    },
    # --------------------------------------------------------------- English
    "en": {
        "difficulty.introductory": "Introductory",
        "difficulty.easy": "Easy",
        "difficulty.intermediate": "Intermediate",
        "difficulty.hard": "Hard",
        "kind.cpp": "C++",
        "kind.python": "Python",
        "minutes_estimate": "≈{n} min",
        "must_handle": "Requirements",
        "example": "Example",
        "input_label": "input",
        "output_label": "output",
        "references": "References",
        "badge_on_completion": "Badge on completion",
        "badge_line": "🏅 Badge on completion: {badge}",
        "edit_cell_below": "Edit the cell below, then press {key1}+{key2}. Your code is saved automatically.",
        "edit_file_then_check": "Edit {path}, then run {cmd}.",
        "start_here": "Start here: {cmd}",
        "statement_edit_line": "  Edit:  {path}",
        "statement_then_line": "  Then:  rk.check('{exercise_id}')",
        "status.passed": "Solved",
        "status.failed": "Not yet",
        "status.compile_error": "Compile error",
        "status.runtime_error": "Runtime error",
        "status.solution_error": "Code error",
        "status.timeout": "Timeout",
        "status.check_result": "Check result",
        "next.passed": "All visible tests pass.\nYour solution has been saved locally.",
        "next.failed": "Start with the first failing case: compare what it expected with what your code produced.",
        "next.compile_error": "Fix the first compiler error shown below, then run this cell again.",
        "next.runtime_error": "Use the runtime message below to identify where execution stopped.",
        "next.solution_error": "Fix the first error in your code, then run this cell again.",
        "next.timeout": "Check for a loop or operation that never terminates.",
        "next.default": "Inspect the details below, then run the cell again.",
        "harness_signature_note": "The harness reported this. Check that your function signature exactly matches the problem statement.",
        "expected_got": "Expected <code>{expected}</code>; got <code>{actual}</code>.",
        "tests_label": "Tests",
        "preview_alt_default": "Histogram produced by your code",
        "your_output": "Your output",
        "reproduce_outside_jupyter": "Reproduce outside Jupyter",
        "logs_line": "Logs: {build} · {run}",
        "need_hint": "Need a hint?",
        "new_badge": "New badge:",
        "continue": "Continue →",
        "continue_help": "Your progress will also be reflected on the local catalog page.",
        "harness_signature_note_text": "(the error is in the harness, which usually means your function signature differs from the one requested)",
        "stderr_tail": "stderr (tail):",
        "preview_saved_text": "  preview: {path}",
        "logs_reproduce_text": "  logs: {work}/build.log, run.log   ·   reproduce: sh {work}/compile.sh",
        "expected_got_text": "   expected {expected}, got {actual}",
        "no_solution_yet": "No solution yet. Run rk.start('{exercise_id}') first (it creates {path}).",
        "keeping_existing": "(keeping your existing {path})",
        "created_path": "Created {path}",
        "no_hints": "No hints for this exercise.",
        "hint_n": "hint {i}/{n}: {hint}",
        "magic_usage": "usage: %%kata <exercise-id>",
        "magic_loaded": "root_kata loaded: use %%kata <exercise-id> at the top of a cell.",
        "progress_solved": "Solved {n}/{m}",
        "attempts_count": "({n} attempts)",
        "badges_prefix": "Badges:",
        "badges_none": "none yet",
        "badge.first_kata.name": "First Kata",
        "badge.first_kata.desc": "Solve any exercise",
        "badge.first_root_histogram.name": "First ROOT Histogram",
        "badge.first_root_histogram.desc": "Fill your first TH1D",
        "badge.basics_complete.name": "Basics Complete",
        "badge.basics_complete.desc": "Solve every available kata",
        "sum.no_compiler": "No C++ compiler found (tried $CXX, g++, clang++). Install one and re-run doctor().",
        "sum.no_root_config": "root-config not found on PATH. Source ROOT (e.g. `source /path/to/root/bin/thisroot.sh`) before starting Jupyter.",
        "sum.compile_timeout": "Compiler did not finish within {seconds} s",
        "sum.compile_failed": "Compilation failed",
        "sum.compile_failed_at": "Compilation failed at {where}: {msg}",
        "sum.run_timeout": "Your program ran longer than {seconds} s (infinite loop?)",
        "sum.crashed_signal": "Your program crashed: {signal}",
        "sum.crashed_exit": "Your program crashed: exit code {code}",
        "sum.segv_hint": " (segfault: probably an out-of-range index, a null pointer, or an uninitialised histogram)",
        "sum.harness_no_json": "The harness did not produce JSON on its last stdout line. Check run.log (did you print something after rk::done()?).",
        "sum.tests_passed": "{n}/{m} tests passed",
        "sum.missing_req": "Missing runtime requirement: {names}",
        "sum.exec_timeout": "Execution exceeded {seconds} s",
        "sum.grader_failed": "The grading worker failed",
        "sum.grader_bad_output": "The grading worker returned invalid output",
        "val.values_differ": "Values differ",
        "val.not_close": "Values are not close",
        "val.case_passed": "Passed",
        "lab_prepared": "prepared {path}",
        "lab_url": "ROOT Kata Jupyter: {url}",
        "lab_stop_hint": "Open that URL in your browser. Press Ctrl-C here to stop.",
        "config_current": "Current language: {lang}",
        "config_set": "Language changed to: {lang}",
        "config_invalid": "Unsupported language: {lang} (use: es, en)",
        "label.python": "Python",
        "label.notebook": "Notebook",
        "label.package": "Package",
        "label.entry_point": "Entry point",
        "label.jupyter": "Jupyter",
        "label.compiler": "Compiler",
        "label.root": "ROOT",
        "label.root_build": "ROOT build",
        "label.pyroot": "PyROOT",
        "label.workspace": "Workspace",
        "label.exercises": "Exercises",
        "doc.entry_point_ok": "matches this environment",
        "doc.entry_point_missing": "root-kata command not found on PATH",
        "doc.fix_reinstall": "activate this conda environment, then reinstall with its own `python -m pip install -e .`",
        "doc.fix_foreign": "remove the foreign copy (e.g. `python -m pip uninstall root-kata` outside conda) and reinstall inside the root-kata env",
        "doc.package_missing": "not importable ({exc})",
        "doc.fix_package": "run `{python} -m pip install -e .` inside this environment",
        "doc.jupyter_missing": "jupyterlab not importable — `root-kata lab` needs it in this environment",
        "doc.compiler_missing": "no g++/clang++ found",
        "doc.fix_compiler": "install a C++ compiler in this environment",
        "doc.root_found": "root-config found, ROOT {version} at {path}",
        "doc.root_missing": "root-config not on PATH — ROOT katas disabled",
        "doc.fix_root": "activate the root-kata conda environment before launching Jupyter",
        "doc.root_build_fail": "a trivial ROOT program does not compile",
        "doc.fix_same_env": "check that compiler and ROOT come from the same environment",
        "doc.root_build_ok": "compiles and runs",
        "doc.root_build_runtime_fail": "compiles but fails at runtime",
        "doc.pyroot_ok": "importable",
        "doc.pyroot_missing": "not importable (C++ warm-ups still work)",
        "doc.workspace": "solutions in ./{kata_dir}/<id>/ · logs in ./.root-kata/<id>/ · progress in {home}",
        "doc.exercises": "{n} available",
        "doc.fix_exercises": "reinstall the package",
    },
}


def home() -> Path:
    p = Path(os.environ.get("ROOT_KATA_HOME", "~/.root-kata")).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return home() / "config.json"


def _config() -> dict[str, Any]:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def normalize(lang: str | None) -> str | None:
    if lang is None:
        return None
    lang = str(lang).strip().lower()
    return lang if lang in LANGS else None


def get_lang() -> str:
    """Active language: env override > config file > default."""
    env = normalize(os.environ.get("ROOT_KATA_LANG"))
    if env:
        return env
    stored = normalize(_config().get("language"))
    return stored or DEFAULT_LANG


def set_lang(lang: str) -> str:
    chosen = normalize(lang)
    if not chosen:
        raise ValueError(t("config_invalid", lang=lang))
    cfg = _config()
    cfg["language"] = chosen
    config_path().write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return chosen


def t(key: str, **kwargs: Any) -> str:
    """Translate a string id in the active language, falling back to en/key."""
    lang = get_lang()
    template = _STRINGS.get(lang, {}).get(key) or _STRINGS["en"].get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
