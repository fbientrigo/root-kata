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

La ruta inicial empieza desde cero y tiene seis ejercicios:

1. **Hola, mundo** — `std::cout` y validación de que todo el entorno funciona.
2. **Lee un valor de un arreglo** — acceso con `[]` a un arreglo fijo.
3. **Imprime un arreglo** — conecta valores almacenados con la salida del programa.
4. **Suma valores positivos** — bucle + condición + acumulador sobre `std::vector`.
5. **Cuenta valores sobre un corte** — selección con un umbral estricto.
6. **Llena un histograma ROOT** — creación y llenado de un `TH1D`.

Los tres primeros son **Introductorios** y no requieren conocer `std::vector`. Sirven tanto para quien nunca programó en C++ como para comprobar rápidamente que instalación, compilación, Jupyter y tests funcionan antes de entrar a ROOT.

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

ROOT Kata está en **español** por defecto, con inglés disponible como idioma completo:

```bash
root-kata config --lang en   # cambia la interfaz a inglés
root-kata config             # muestra el idioma actual
```

Para pruebas puntuales, `ROOT_KATA_LANG=en root-kata ...` tiene prioridad sobre la configuración.

La preferencia vive en `~/.root-kata/config.json`. El progreso (`~/.root-kata/progress.json`) nunca depende del idioma: guarda identificadores estables (ids de ejercicio e insignias), así que cambiar de idioma no duplica insignias ni katas resueltos. Las insignias antiguas que usaban nombres en inglés se migran automáticamente a ids.

## Abrir los ejercicios

Catálogo web:

**https://fbientrigo.github.io/root-kata/**

La web muestra tu progreso local (se guarda en el navegador), el catálogo de katas y un botón **Abrir en Jupyter** por ejercicio que abre directamente el cuaderno de ese kata en `127.0.0.1:8888`. Requiere `root-kata lab` corriendo.

El flujo completo:

1. abre el catálogo y elige un kata;
2. pulsa **Abrir en Jupyter** — se abre exactamente ese cuaderno;
3. ejecuta la celda con `Shift+Enter`: aparece el enunciado y debajo una celda editable;
4. edita la celda y vuelve a ejecutar `Shift+Enter`;
5. al resolver, pulsa **Continuar →** para registrar el progreso en la web del catálogo.

Si el botón no puede abrir Jupyter, copia el comando mostrado:

```python
import root_kata as rk
rk.start("cpp-hello-world")
```

Pégalo en una celda de Python y ejecuta `Shift+Enter`.

`rk.start(...)` muestra el enunciado e inserta debajo una celda editable con el starter C++:

```cpp
%%kata cpp-hello-world
#include <iostream>

void say_hello() {
}
```

Edita esa misma celda y vuelve a ejecutar `Shift+Enter`. ROOT Kata guarda la solución, compila C++ real, ejecuta los tests visibles y muestra el progreso.

Cuando todos pasan, el kata queda resuelto localmente.

## Si `Abrir en Jupyter` no funciona

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

La regla importante es simple: **ROOT, Python, JupyterLab y ROOT Kata deben vivir en el mismo entorno**. Un `pip install` sin el `python -m` puede instalar ROOT Kata en otro Python mientras `import root_kata` falla dentro del entorno. `root-kata doctor` detecta exactamente ese desajuste.

## Comandos útiles

Desde Jupyter:

```python
rk.show("cpp-hello-world")
rk.tests("cpp-hello-world")
rk.hint("cpp-hello-world")
rk.progress()
rk.export()
```

Desde terminal:

```bash
root-kata lab
root-kata doctor
root-kata list
root-kata config --lang es|en
root-kata start cpp-hello-world
root-kata check cpp-hello-world
root-kata progress
```

## Cómo funciona un kata C++

```text
solution.cpp del alumno
        +
harness.cpp del ejercicio
        ↓
g++ + root-config cuando corresponde
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
python -m pip install -e .
python -m unittest discover -s tests -v
```

Los tests que requieren ROOT se omiten automáticamente cuando `root-config` o PyROOT no están disponibles. El workflow de CI comprueba el motor portable y que la web pueda generarse desde sus fuentes.

## GitHub Pages

La web de `docs/` es HTML/CSS/JavaScript estático, sin framework, CDN, backend, login ni analytics. Se genera con `python scripts/build_pages.py` (español en la raíz, inglés bajo `en/`) y se publica mediante el workflow `pages.yml` (Source: **GitHub Actions**). El progreso mostrado en la web vive solo en el `localStorage` de tu navegador; se actualiza con el botón **Continuar →** del cuaderno al resolver un kata.

## Principios del proyecto

- una sola ruta de instalación soportada para estudiantes;
- cero cuentas y cero cloud runner;
- tests visibles y feedback causal;
- C++ y ROOT reales;
- pocas abstracciones y pocas dependencias;
- una experiencia rica sin convertir el proyecto en una plataforma pesada.

## Fuera de alcance por ahora

Sandbox para código hostil, leaderboard, cuentas, ejecución remota, hidden tests y una plataforma LMS.
