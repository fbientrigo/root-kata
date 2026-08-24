from __future__ import annotations
import platform,shutil,subprocess,sys
from pathlib import Path
from . import progress
from .catalog import list_exercises
from .cpp_runner import _which_compiler,root_config_flags

def doctor(kata_dir:Path,*,in_notebook:bool)->bool:
    ok_all=True
    def line(name:str,ok:bool|None,detail:str,fix:str="")->None:
        nonlocal ok_all
        mark="✅" if ok else ("⚠️ " if ok is None else "❌")
        if ok is False:ok_all=False
        print(f"{mark} {name:<12} {detail}"+(f"\n              → {fix}" if fix and not ok else ""))
    line("Python",True,f"{sys.version.split()[0]} on {platform.system()} {platform.machine()}"); line("Notebook",True,"running in Jupyter" if in_notebook else "terminal (fine; HTML cards appear in Jupyter)")
    cxx=_which_compiler()
    if cxx: line("Compiler",True,subprocess.run([cxx,"--version"],capture_output=True,text=True).stdout.splitlines()[0])
    else: line("Compiler",False,"no g++/clang++ found","install a C++ compiler in this environment")
    flags=root_config_flags()
    if flags:
        rv=subprocess.run(["root-config","--version"],capture_output=True,text=True).stdout.strip(); line("ROOT",True,f"root-config found, ROOT {rv} at {shutil.which('root-config')}")
        if cxx:
            try:
                import tempfile
                with tempfile.TemporaryDirectory() as t:
                    src=Path(t)/"t.cpp"; exe=Path(t)/"t"; src.write_text('#include "TH1D.h"\nint main(){TH1D h("h","",1,0,1);h.Fill(0.5);return h.GetEntries()==1?0:1;}\n')
                    b=subprocess.run([cxx,*flags[0],"-o",str(exe),str(src),*flags[1]],capture_output=True,text=True,timeout=120)
                    if b.returncode!=0: line("ROOT build",False,"a trivial ROOT program does not compile","check that compiler and ROOT come from the same environment")
                    else:
                        rr=subprocess.run([str(exe)],capture_output=True,timeout=30); line("ROOT build",rr.returncode==0,"compiles and runs" if rr.returncode==0 else "compiles but fails at runtime")
            except Exception as exc: line("ROOT build",False,f"smoke test failed: {exc}")
    else: line("ROOT",None,"root-config not on PATH — ROOT katas disabled","activate the root-kata conda environment before launching Jupyter")
    try:
        import ROOT
        line("PyROOT",True,"importable")
    except Exception: line("PyROOT",None,"not importable (C++ warm-ups still work)")
    line("Workspace",True,f"solutions in ./{kata_dir}/<id>/ · logs in ./.root-kata/<id>/ · progress in {progress.home()}"); n=len(list_exercises()); line("Exercises",n>0,f"{n} available","reinstall the package"); return ok_all
