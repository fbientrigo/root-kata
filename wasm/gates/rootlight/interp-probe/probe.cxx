// DIAGNOSTIC PROBE, NOT AN INTERPRETER AND NOT SHIPPABLE.
//
// It answers one question: which TInterpreter services does a P0 TH1D program actually call?
// Every pure virtual of ROOT's TInterpreter is overridden by generated code (gen_stub.py) that
// logs its name and returns a default value. Nothing is implemented. Any ROOT behaviour that
// depends on a real interpreter is therefore WRONG here by construction -- results of the P0
// calls are printed only to see how far execution gets, never as evidence of correctness.
#include <cstdio>
#include <cstdlib>
#include "TInterpreter.h"
#include "TApplication.h"

static FILE *rklog = nullptr;
static void rklog_open() { if (!rklog) { const char *p = getenv("RK_INTERP_LOG"); rklog = p ? fopen(p, "w") : stderr; if (!rklog) rklog = stderr; } }
#define RKLOG(name) do { rklog_open(); fprintf(rklog, "TInterpreter::%s\n", name); fflush(rklog); } while (0)

class TStubInterpreter : public TInterpreter {
public:
   TStubInterpreter(const char *name, const char *title) : TInterpreter(name, title) { RKLOG("ctor"); }
#include "stub_methods.inc"
};

extern "C" TInterpreter *CreateInterpreter(void * /*shlibHandle*/, const char * /*argv*/[])
{
   RKLOG("CreateInterpreter");
   return new TStubInterpreter("stub", "diagnostic stub interpreter (not an interpreter)");
}

extern "C" void *DestroyInterpreter(TInterpreter *interp) { RKLOG("DestroyInterpreter"); delete interp; return nullptr; }
