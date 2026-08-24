from __future__ import annotations
import platform,shutil,subprocess,sys
from pathlib import Path
from . import i18n,progress
from .catalog import list_exercises
from .cpp_runner import _which_compiler,root_config_flags

def _entry_point_mismatch()->str|None:
    """The classic failure: `root-kata` resolves to another Python environment."""
    rk=shutil.which("root-kata")
    if not rk:return "root-kata command not found on PATH"
    if Path(rk).resolve().parent!=Path(sys.executable).resolve().parent:
        return f"root-kata runs from {Path(rk).resolve().parent} but this Python is {Path(sys.executable).resolve().parent}"
    return None

def doctor(kata_dir:Path,*,in_notebook:bool)->bool:
    t=i18n.t; ok_all=True
    def line(name:str,ok:bool|None,detail:str,fix:str="")->None:
        nonlocal ok_all
        mark="✅" if ok else ("⚠️ " if ok is None else "❌")
        if ok is False:ok_all=False
        print(f"{mark} {name:<12} {detail}"+(f"\n              → {fix}" if fix and not ok else ""))
    line(t("label.python"),True,f"{sys.version.split()[0]} at {sys.executable}")
    line(t("label.notebook"),True,"running in Jupyter" if in_notebook else "terminal (fine; HTML cards appear in Jupyter)")
    try:
        import root_kata
        line(t("label.package"),True,str(Path(root_kata.__file__).resolve()))
    except Exception as exc:
        line(t("label.package"),False,t("doc.package_missing",exc=exc),t("doc.fix_package",python=Path(sys.executable).name))
    m=_entry_point_mismatch()
    fix=t("doc.fix_reinstall") if m=="root-kata command not found on PATH" else t("doc.fix_foreign")
    line(t("label.entry_point"),m is None,m or t("doc.entry_point_ok"),"" if m is None else fix)
    try:
        import jupyterlab
        line(t("label.jupyter"),True,f"jupyterlab {jupyterlab.__version__}")
    except Exception:
        line(t("label.jupyter"),None,t("doc.jupyter_missing"))
    cxx=_which_compiler()
    if cxx: line(t("label.compiler"),True,subprocess.run([cxx,"--version"],capture_output=True,text=True).stdout.splitlines()[0])
    else: line(t("label.compiler"),False,t("doc.compiler_missing"),t("doc.fix_compiler"))
    flags=root_config_flags()
    if flags:
        rv=subprocess.run(["root-config","--version"],capture_output=True,text=True).stdout.strip(); line(t("label.root"),True,t("doc.root_found",version=rv,path=shutil.which("root-config")))
        if cxx:
            try:
                import tempfile
                with tempfile.TemporaryDirectory() as tmp:
                    src=Path(tmp)/"t.cpp"; exe=Path(tmp)/"t"; src.write_text('#include "TH1D.h"\nint main(){TH1D h("h","",1,0,1);h.Fill(0.5);return h.GetEntries()==1?0:1;}\n')
                    b=subprocess.run([cxx,*flags[0],"-o",str(exe),str(src),*flags[1]],capture_output=True,text=True,timeout=120)
                    if b.returncode!=0: line(t("label.root_build"),False,t("doc.root_build_fail"),t("doc.fix_same_env"))
                    else:
                        rr=subprocess.run([str(exe)],capture_output=True,timeout=30)
                        line(t("label.root_build"),rr.returncode==0,t("doc.root_build_ok") if rr.returncode==0 else t("doc.root_build_runtime_fail"))
            except Exception as exc: line(t("label.root_build"),False,f"smoke test failed: {exc}")
    else: line(t("label.root"),None,t("doc.root_missing"),t("doc.fix_root"))
    try:
        import ROOT
        line(t("label.pyroot"),True,t("doc.pyroot_ok"))
    except Exception: line(t("label.pyroot"),None,t("doc.pyroot_missing"))
    line(t("label.workspace"),True,t("doc.workspace",kata_dir=kata_dir,home=progress.home()))
    n=len(list_exercises()); line(t("label.exercises"),n>0,t("doc.exercises",n=n),t("doc.fix_exercises")); return ok_all
