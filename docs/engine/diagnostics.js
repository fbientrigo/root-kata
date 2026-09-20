/**
 * Compiler diagnostics parser for Clang-Repl / CppInterOp in WebAssembly.
 * Extracts structured errors/warnings and formats source context.
 */

const DIAGNOSTIC_RE = /^(?:.+[/\\])?([^:\n]+):(\d+):(?:(\d+):)?\s*(error|warning|note):\s*(.+)$/gm;

/**
 * @typedef {Object} CompilerDiagnostic
 * @property {string} file
 * @property {number} line
 * @property {number} [column]
 * @property {'error'|'warning'|'note'} severity
 * @property {string} message
 * @property {string} raw
 */

/**
 * Parse Clang diagnostic lines from stderr / diagnostic output.
 * @param {string} text
 * @returns {CompilerDiagnostic[]}
 */
export function parseDiagnostics(text) {
  if (!text) return [];
  const results = [];
  const re = new RegExp(DIAGNOSTIC_RE.source, 'gm');
  let match;
  while ((match = re.exec(text)) !== null) {
    results.push({
      file: match[1].trim(),
      line: parseInt(match[2], 10),
      column: match[3] ? parseInt(match[3], 10) : undefined,
      severity: /** @type {'error'|'warning'|'note'} */ (match[4]),
      message: match[5].trim(),
      raw: match[0].trim(),
    });
  }
  return results;
}

/**
 * Extract the first relevant compiler error and attach source context lines.
 * @param {CompilerDiagnostic[]} diagnostics
 * @param {string} studentCode
 * @param {string} [preferredFile='solution.cpp']
 * @returns {Object|null}
 */
export function extractFirstError(diagnostics, studentCode, preferredFile = 'solution.cpp') {
  if (!diagnostics || diagnostics.length === 0) return null;

  const errors = diagnostics.filter((d) => d.severity === 'error');
  if (errors.length === 0) return null;

  const studentHits = errors.filter((d) => d.file === preferredFile);
  const target = studentHits.length > 0 ? studentHits[0] : errors[0];

  const inStudentFile = target.file === preferredFile;
  const contextLines = [];

  if (inStudentFile && studentCode) {
    const lines = studentCode.split('\n');
    const targetLine = target.line;
    const start = Math.max(1, targetLine - 2);
    const end = Math.min(lines.length, targetLine + 2);

    for (let n = start; n <= end; n++) {
      const marker = n === targetLine ? '>' : ' ';
      const padNum = String(n).padStart(4, ' ');
      contextLines.push(`${marker} ${padNum} | ${lines[n - 1]}`);
    }
  }

  return {
    file: target.file,
    line: target.line,
    column: target.column,
    message: target.message,
    context: contextLines.join('\n'),
    in_student_file: inStudentFile,
  };
}
