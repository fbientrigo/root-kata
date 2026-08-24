# ROOT Kata

**Ejercicios cortos y comprobables de C++/ROOT que se resuelven en Jupyter usando el compilador y ROOT de tu propia máquina.**

> Prototipo educativo no oficial. No está afiliado ni respaldado por CERN.

## Qué es

ROOT Kata busca que practicar ROOT se parezca a resolver un problema pequeño en LeetCode/HackerRank, pero sin cuentas, servidores ni infraestructura extra:

1. lees un problema breve;
2. lo abres en Jupyter;
3. completas una función;
4. ejecutas la celda con `Shift+Enter`;
5. ves cuántos tests pasan y corriges lo que falla.

La ruta inicial tiene solo tres ejercicios:

1. **Sum positive values** — loop + condición + acumulador.
2. **Count values above a cut** — selección con un threshold estricto.
3. **Fill a ROOT histogram** — creación y llenado de un `TH1D`.

La progresión es intencionalmente pequeña: **acumular → seleccionar → histogramar**.

## Instalación

Requisito único: **conda** (o `mamba`/`micromamba`). Si no lo tienes, instala [Miniforge](https://github.com/conda-forge/miniforge) y vuelve aquí.

```bash
git clone https://github.com/fbientrigo/root-kata.git
cd root-kata
./install.sh
```

El instalador crea el entorno `root-kata` (Python 3.12 + CERN ROOT + JupyterLab), instala ROOT Kata con el Python del propio entorno y verifica que todo vive en el mismo lugar.

Cada sesión empieza así:

```bash
conda activate root-kata
root-kata lab
```

Eso arranca JupyterLab en `http://127.0.0.1:8888/lab` sin abrir navegador desde la terminal. Mantén esa terminal abierta mientras trabajas.

## Idioma

ROOT Kata está en **español** por defecto, con inglés disponible como primer-class:

```bash
root-kata config --lang en   # cambia la interfaz a inglés
root-kata config             # muestra el idioma actual
```

Para pruebas puntuales, `ROOT_KATA_LANG=en root-kata ...` tiene prioridad sobre la configuración.

La preferencia vive en `~/.root-kata/config.json`. El progreso (`~/.root-kata/progress.json`) nunca depende del idioma: guarda identificadores estables (ids de ejercicio e insignias), así que cambiar de idioma no duplica insignias ni katas resueltos. Las insignias antiguas que usaban nombres en inglés se migran automáticamente a ids.

## Abrir los ejercicios

Catálogo web temporal:

**https://fbientrigo.github.io/root-kata/**

Elige un problema y pulsa **Open in Jupyter**. La página abre Jupyter local en `127.0.0.1:8888` e intenta copiar un comando como:

```python
import root_kata as rk
rk.start("cpp-sum-positive")
```

Pégalo en una celda de Python y ejecuta `Shift+Enter`.

`rk.start(...)` muestra el enunciado e inserta debajo una celda editable con el starter C++:

```cpp
%%kata cpp-sum-positive
#include <vector>

double sum_positive(const std::vector<double>& values) {
    // TODO
    return 0;
}
```

Edita esa misma celda y vuelve a ejecutar `Shift+Enter`. ROOT Kata guarda la solución, compila C++ real, ejecuta los tests visibles y muestra el progreso:

```text
Tests passed                              3 / 4
████████████████████████████░░░░░░░░░

✓ empty input
✕ mixed signs — expected 8, got 6
✓ all negative
✓ all positive
```

Cuando todos pasan, el kata queda resuelto localmente.

## Si `Open in Jupyter` no funciona

La web pública no controla tu Jupyter local. El botón presupone que Jupyter está corriendo en el puerto `8888`:

```bash
conda activate root-kata
root-kata lab
```

### Instalación manual (alternativa)

Si prefieres hacerlo paso a paso, o `./install.sh` falló y quieres ver dónde:

```bash
conda env create -f environment.yml   # o: conda env update -f environment.yml si ya existe
conda activate root-kata
python -m pip install -e .            # siempre `python -m pip`, nunca un `pip` suelto
root-kata doctor
```

La regla importante es simple: **ROOT, Python, JupyterLab y ROOT Kata deben vivir en el mismo entorno**. Un `pip install` sin el `python -m` puede instalar ROOT Kata en otro Python (por ejemplo, uno de usuario) mientras `import root_kata` falla dentro del entorno. `root-kata doctor` detecta exactamente ese desajuste.

## Comandos útiles

Desde Jupyter:

```python
rk.show("cpp-sum-positive")
rk.tests("cpp-sum-positive")
rk.hint("cpp-sum-positive")
rk.progress()
rk.export()
```

Desde terminal:

```bash
root-kata lab
root-kata doctor
root-kata list
root-kata config --lang es|en
root-kata start cpp-sum-positive
root-kata check cpp-sum-positive
root-kata progress
```

## Cómo funciona un kata C++

```text
solution.cpp del alumno
        +
harness.cpp del ejercicio
        ↓
g++ + root-config
        ↓
ejecutable local
        ↓
resultados JSON
        ↓
validator.py
        ↓
✓ / ✕ por test
```

No hay ejecución en la nube ni tests escondidos. `compile.sh` conserva el comando exacto utilizado para poder reproducir un error fuera de ROOT Kata.

## Escribir problemas

Cada ejercicio vive en `src/root_kata/exercises/<id>/` y puede incluir:

- `exercise.json`: metadata, dificultad, topics, ejemplos y links;
- `problem.md`: enunciado legible;
- `solution.cpp`: starter del alumno;
- `harness.cpp`: casos ejecutados;
- `validator.py`: expectativas de cada test.

Hay dos plantillas mínimas:

- `docs/templates/problem.md`
- `docs/templates/problem.adoc`

Después de modificar metadata o problemas públicos, regenera GitHub Pages:

```bash
python scripts/build_pages.py
```

## Desarrollo

El paquete Python no tiene dependencias runtime adicionales:

```bash
pip install -e .
python -m unittest discover -s tests -v
```

Los tests que requieren ROOT se omiten automáticamente cuando `root-config` o PyROOT no están disponibles. El workflow de CI comprueba el motor portable y que `docs/` esté sincronizado con sus fuentes.

## GitHub Pages

La web de `docs/` es HTML/CSS/JavaScript estático, sin framework, CDN, backend, login ni analytics.

El workflow `pages.yml` publica `docs/` mediante GitHub Pages. Para un repositorio nuevo puede ser necesario seleccionar una sola vez **Settings → Pages → Source → GitHub Actions**.

## Principios del proyecto

- una sola ruta de instalación soportada para estudiantes;
- cero cuentas y cero cloud runner;
- tests visibles y feedback causal;
- C++ y ROOT reales;
- pocas abstracciones y pocas dependencias;
- una experiencia rica sin convertir el proyecto en una plataforma pesada.

## Fuera de alcance por ahora

Sandbox para código hostil, leaderboard, cuentas, ejecución remota, hidden tests y una plataforma LMS.
