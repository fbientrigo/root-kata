from __future__ import annotations
from dataclasses import dataclass
import math,time
from typing import Any,Callable
class ExpectationError(AssertionError):
    def __init__(self,message:str,*,actual:Any=None,expected:Any=None):super().__init__(message);self.actual=actual;self.expected=expected
def _display(value:Any)->str|None:
    if value is None:return None
    text=repr(value);return text if len(text)<=500 else text[:497]+"..."
def expect(condition:bool,message:str,*,actual:Any=None,expected:Any=None)->None:
    if not condition:raise ExpectationError(message,actual=actual,expected=expected)
def expect_equal(actual:Any,expected:Any,message:str|None=None)->None:
    if actual!=expected:raise ExpectationError(message or "Values differ",actual=actual,expected=expected)
def expect_close(actual:float,expected:float,*,rel_tol:float=1e-9,abs_tol:float=1e-9,message:str|None=None)->None:
    if not math.isclose(float(actual),float(expected),rel_tol=rel_tol,abs_tol=abs_tol):raise ExpectationError(message or "Values are not close",actual=actual,expected=expected)
@dataclass(frozen=True)
class Case:
    name:str;check:Callable[[],None]
    def run(self)->dict[str,Any]:
        started=time.perf_counter()
        try:self.check()
        except ExpectationError as exc:return {"name":self.name,"passed":False,"message":str(exc),"actual":_display(exc.actual),"expected":_display(exc.expected),"duration_ms":round((time.perf_counter()-started)*1000,2)}
        except Exception as exc:return {"name":self.name,"passed":False,"message":f"{type(exc).__name__}: {exc}","actual":None,"expected":None,"duration_ms":round((time.perf_counter()-started)*1000,2)}
        return {"name":self.name,"passed":True,"message":"Passed","actual":None,"expected":None,"duration_ms":round((time.perf_counter()-started)*1000,2)}
def case(name:str,check:Callable[[],None])->Case:return Case(name=name,check=check)
