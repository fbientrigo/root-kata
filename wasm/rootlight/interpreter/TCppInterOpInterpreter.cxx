#include "TCppInterOpInterpreter.h"

#include <cstdio>
#include <stdexcept>
#include <string>
#include <sys/stat.h>

#include <CppInterOp/CppInterOp.h>

#include "TError.h"

////////////////////////////////////////////////////////////////////////////////
/// Report an interpreter service that wasm ROOT does not implement yet.

void rkUnsupported(const char *service)
{
   std::string msg = std::string("TInterpreter::") + service +
                     " is not implemented in wasm ROOT yet";
   // Two channels on purpose: ROOT's own error stream, so the message looks like
   // every other ROOT diagnostic, and an exception, so execution cannot continue
   // as if the call had succeeded.
   ::Error("TCppInterOpInterpreter", "%s", msg.c_str());
   throw std::runtime_error(msg);
}

////////////////////////////////////////////////////////////////////////////////
/// Attach to the compiler the browser kernel already runs. We never create one.

TCppInterOpInterpreter::TCppInterOpInterpreter(const char *name, const char *title)
   : TInterpreter(name, title)
{
   fInterp = Cpp::GetInterpreter();
   if (!fInterp) {
      // Without a host interpreter there is nothing to adapt, and pretending
      // otherwise would make every later answer fiction.
      ::Error("TCppInterOpInterpreter",
              "no CppInterOp interpreter in this process; wasm ROOT must run inside a "
              "kernel that already created one");
      throw std::runtime_error("TCppInterOpInterpreter: Cpp::GetInterpreter() returned null");
   }
}

////////////////////////////////////////////////////////////////////////////////
/// ROOT calls this once, after construction, before any interpreter use.

void TCppInterOpInterpreter::Initialize()
{
   // The kernel's clang-repl is already initialized and already has its include
   // paths; RegisterModule adds ROOT's. Nothing further is required here, and
   // anything we invented would be untruthful about what this adapter does.
}

////////////////////////////////////////////////////////////////////////////////
/// Release our side of the adapter. The compiler belongs to the kernel.

void TCppInterOpInterpreter::ShutDown()
{
   fModules.clear();
}

namespace {
bool PathExists(const char *p)
{
   struct stat st;
   return p && *p && ::stat(p, &st) == 0;
}
}   // namespace

////////////////////////////////////////////////////////////////////////////////
/// Register one ROOT dictionary.
///
/// Called by the generated dictionary of every loaded ROOT library
/// (`TriggerDictionaryInitialization_libX_Impl` -> `TROOT::RegisterModule`).
///
/// These dictionaries are generated with `-writeEmptyRootPCM`, so `payloadCode`
/// and `fwdDeclsCode` arrive as nullptr and the content is the header list.
/// When they are not null we declare them to the real compiler; recording them
/// without declaring them would be a silent no-op.

void TCppInterOpInterpreter::RegisterModule(const char *modulename, const char **headers,
                                            const char **includePaths, const char *payloadCode,
                                            const char *fwdDeclsCode, void (* /*triggerFunc*/)(),
                                            const FwdDeclArgsToKeepCollection_t & /*fwdDeclArgsToKeep*/,
                                            const char ** /*classesHeaders*/,
                                            Bool_t /*lateRegistration*/, Bool_t /*hasCxxModule*/)
{
   Module mod;
   mod.fName = modulename ? modulename : "";

   // The include paths baked into a generated dictionary are the *build*
   // machine's absolute paths, which do not exist in the browser filesystem.
   // Add the ones that do resolve here and skip the rest rather than polluting
   // the compiler's search path with directories that cannot be read.
   for (const char **p = includePaths; p && *p; ++p)
      if (PathExists(*p))
         Cpp::AddIncludePath(*p);

   for (const char **h = headers; h && *h; ++h)
      mod.fHeaders.emplace_back(*h);

   auto declare = [&](const char *code, const char *what) {
      if (!code || !*code)
         return;
      if (Cpp::Declare(code) != 0) {
         std::string msg = std::string("could not declare the ") + what + " of dictionary " +
                           mod.fName;
         ::Error("TCppInterOpInterpreter::RegisterModule", "%s", msg.c_str());
         throw std::runtime_error(msg);
      }
   };
   declare(fwdDeclsCode, "forward declarations");
   declare(payloadCode, "payload");

   fModules.push_back(std::move(mod));
}

////////////////////////////////////////////////////////////////////////////////
/// ROOT's interpreter plugin entry points (core/base/src/TROOT.cxx:2251-2262).

extern "C" TInterpreter *CreateInterpreter(void * /*shlibHandle*/, const char * /*argv*/[])
{
   return new TCppInterOpInterpreter("cppinterop", "CppInterOp/clang-repl interpreter for wasm ROOT");
}

extern "C" void *DestroyInterpreter(TInterpreter *interp)
{
   delete interp;
   return nullptr;
}

//==============================================================================
// M4: compiling and calling a TFormula.
//
// TFormula::InputFormulaIntoCling (hist/hist/src/TFormula.cxx:944-961) declares
// its generated C++ here; TMethodCall (core/meta/src/TMethodCall.cxx:184-350)
// then resolves that function and asks for a pointer it can call. ROOT's
// calling convention for such a pointer is
//     void (*)(void *self, int nargs, void **args, void *result)
// with args[i] pointing *at* argument i (TFormula.cxx:3518-3527).
//==============================================================================

namespace {

/// What ROOT calls a ClassInfo_t: a scope in the interpreter.
struct RkClassInfo {
   Cpp::TCppScope_t fScope = nullptr;
};

/// What ROOT calls a CallFunc_t: a resolved function plus its callable wrapper.
struct RkCallFunc {
   Cpp::TCppFunction_t fFunc = nullptr;
   TInterpreter::CallFuncIFacePtr_t::Generic_t fGeneric = nullptr;
};

RkClassInfo *CI(ClassInfo_t *p) { return reinterpret_cast<RkClassInfo *>(p); }
RkCallFunc *CF(CallFunc_t *p) { return reinterpret_cast<RkCallFunc *>(p); }

/// Build a wrapper with ROOT's calling convention around `func`, compile it, and
/// return its address.
///
/// This is how ROOT's own TCling does it: emit a small extern "C" shim whose
/// signature is the one ROOT calls, let the interpreter compile it, then take
/// its address. Reaching into CppInterOp's JitCall for its private wrapper
/// pointer would depend on that class's internal layout; this does not.
///
/// Returns nullptr and reports why if the signature is not expressible.
TInterpreter::CallFuncIFacePtr_t::Generic_t MakeRootCallable(Cpp::TCppFunction_t func)
{
   static unsigned long counter = 0;
   const std::string wrapper = "__rk_call_" + std::to_string(counter++);
   const std::string name = Cpp::GetQualifiedName(func);
   const std::string ret = Cpp::GetTypeAsString(Cpp::GetFunctionReturnType(func));
   const size_t nargs = Cpp::GetFunctionNumArgs(func);

   std::string call = name + "(";
   for (size_t i = 0; i < nargs; ++i) {
      const std::string arg = Cpp::GetTypeAsString(Cpp::GetFunctionArgType(func, i));
      if (arg.empty()) {
         ::Error("TCppInterOpInterpreter", "cannot express argument %zu of %s", i, name.c_str());
         return nullptr;
      }
      // args[i] points at the argument, so read it back through its own type.
      call += (i ? ", " : "") + std::string("*(") + arg + " *)args[" + std::to_string(i) + "]";
   }
   call += ")";

   std::string code = "extern \"C\" void " + wrapper +
                      "(void *, size_t, void **args, void *result) { (void)args; ";
   if (ret == "void")
      code += call + "; (void)result;";
   else
      code += "*(" + ret + " *)result = " + call + ";";
   code += " }";

   if (Cpp::Declare(code.c_str()) != 0) {
      ::Error("TCppInterOpInterpreter", "could not compile a call wrapper for %s", name.c_str());
      return nullptr;
   }
   auto addr = Cpp::GetFunctionAddress(wrapper.c_str());
   if (!addr) {
      ::Error("TCppInterOpInterpreter", "call wrapper for %s has no address", name.c_str());
      return nullptr;
   }
   return reinterpret_cast<TInterpreter::CallFuncIFacePtr_t::Generic_t>(addr);
}

}   // namespace

////////////////////////////////////////////////////////////////////////////////
/// Declare code to the interpreter without executing it.

Bool_t TCppInterOpInterpreter::Declare(const char *code)
{
   if (!code || !*code)
      return kFALSE;
   return Cpp::Declare(code) == 0 ? kTRUE : kFALSE;
}

////////////////////////////////////////////////////////////////////////////////
/// Run one line and return its value, as ROOT's interpreter does.
///
/// ROOT uses ProcessLine for both expressions (whose value it wants) and
/// declarations (ROOT's autoparse triggers are a `namespace { ... }` block).
/// Try it as an expression first, then as a declaration. A line that is neither
/// is a genuine user error: report it through ROOT's own error channel and
/// error code rather than throwing, which is what ROOT itself does.

Longptr_t TCppInterOpInterpreter::ProcessLine(const char *line, EErrorCode *error)
{
   if (error)
      *error = kNoError;
   if (!line || !*line)
      return 0;

   bool hadError = false;
   const intptr_t value = Cpp::Evaluate(line, &hadError);
   if (!hadError)
      return static_cast<Longptr_t>(value);

   if (Cpp::Declare(line) == 0)
      return 0;

   ::Error("TCppInterOpInterpreter::ProcessLine", "could not process input");
   if (error)
      *error = kProcessing;
   return 0;
}

Longptr_t TCppInterOpInterpreter::ProcessLineSynch(const char *line, EErrorCode *error)
{
   // Single-threaded runtime: there is nothing to synchronise with.
   return ProcessLine(line, error);
}

Longptr_t TCppInterOpInterpreter::Calc(const char *line, EErrorCode *error)
{
   if (error)
      *error = kNoError;
   if (!line || !*line)
      return 0;
   bool hadError = false;
   const intptr_t value = Cpp::Evaluate(line, &hadError);
   if (hadError) {
      ::Error("TCppInterOpInterpreter::Calc", "could not evaluate input");
      if (error)
         *error = kProcessing;
      return 0;
   }
   return static_cast<Longptr_t>(value);
}

////////////////////////////////////////////////////////////////////////////////
/// Scope handles.

ClassInfo_t *TCppInterOpInterpreter::ClassInfo_Factory(Bool_t /*all*/) const
{
   auto *info = new RkClassInfo;
   info->fScope = Cpp::GetGlobalScope();
   return reinterpret_cast<ClassInfo_t *>(info);
}

ClassInfo_t *TCppInterOpInterpreter::ClassInfo_Factory(ClassInfo_t *cl) const
{
   auto *info = new RkClassInfo;
   if (cl)
      info->fScope = CI(cl)->fScope;
   return reinterpret_cast<ClassInfo_t *>(info);
}

ClassInfo_t *TCppInterOpInterpreter::ClassInfo_Factory(const char *name) const
{
   auto *info = new RkClassInfo;
   info->fScope = (name && *name) ? Cpp::GetScopeFromCompleteName(name) : Cpp::GetGlobalScope();
   return reinterpret_cast<ClassInfo_t *>(info);
}

ClassInfo_t *TCppInterOpInterpreter::ClassInfo_Factory(DeclId_t /*declid*/) const
{
   // Constructing a scope from a ROOT DeclId needs the declaration mapping M4
   // does not build; guessing a scope would silently resolve to the wrong class.
   rkUnsupported("ClassInfo_Factory(DeclId_t)");
}

void TCppInterOpInterpreter::ClassInfo_Init(ClassInfo_t *info, const char *name) const
{
   if (!info)
      return;
   CI(info)->fScope = (name && *name) ? Cpp::GetScopeFromCompleteName(name) : nullptr;
}

void TCppInterOpInterpreter::ClassInfo_Delete(ClassInfo_t *info) const
{
   delete CI(info);
}

Bool_t TCppInterOpInterpreter::ClassInfo_IsValid(ClassInfo_t *info) const
{
   return info && CI(info)->fScope ? kTRUE : kFALSE;
}

////////////////////////////////////////////////////////////////////////////////
/// Callable-function handles.

CallFunc_t *TCppInterOpInterpreter::CallFunc_Factory() const
{
   return reinterpret_cast<CallFunc_t *>(new RkCallFunc);
}

void TCppInterOpInterpreter::CallFunc_Init(CallFunc_t *func) const
{
   if (func)
      *CF(func) = RkCallFunc{};
}

void TCppInterOpInterpreter::CallFunc_Delete(CallFunc_t *func) const
{
   delete CF(func);
}

Bool_t TCppInterOpInterpreter::CallFunc_IsValid(CallFunc_t *func) const
{
   return func && CF(func)->fGeneric ? kTRUE : kFALSE;
}

TInterpreter::CallFuncIFacePtr_t TCppInterOpInterpreter::CallFunc_IFacePtr(CallFunc_t *func) const
{
   if (!func || !CF(func)->fGeneric)
      return CallFuncIFacePtr_t();
   return CallFuncIFacePtr_t(CF(func)->fGeneric);
}

////////////////////////////////////////////////////////////////////////////////
/// Resolve `method` in `info`'s scope and prepare it to be called.
///
/// The prototype string is not used to choose between overloads: this looks the
/// name up and requires the answer to be unambiguous. TFormula's generated
/// functions have unique names, so that is exact for M4's purpose; an ambiguous
/// name fails loudly rather than picking one.

void TCppInterOpInterpreter::CallFunc_SetFuncProto(CallFunc_t *func, ClassInfo_t *info,
                                                   const char *method, const char * /*proto*/,
                                                   bool /*objectIsConst*/, Longptr_t *Offset,
                                                   ROOT::EFunctionMatchMode /*mode*/) const
{
   if (Offset)
      *Offset = 0;
   if (!func || !method || !*method)
      return;
   *CF(func) = RkCallFunc{};

   Cpp::TCppScope_t scope = info && CI(info)->fScope ? CI(info)->fScope : Cpp::GetGlobalScope();
   std::vector<Cpp::TCppFunction_t> candidates;
   Cpp::GetFunctionsUsingName(scope, method).swap(candidates);
   if (candidates.empty())
      return;   // ROOT's own "method not found": CallFunc_IsValid stays false
   if (candidates.size() > 1) {
      ::Error("TCppInterOpInterpreter::CallFunc_SetFuncProto",
              "%s is overloaded; choosing an overload by prototype is not implemented in wasm "
              "ROOT yet", method);
      return;
   }
   CF(func)->fFunc = candidates[0];
   CF(func)->fGeneric = MakeRootCallable(candidates[0]);
}

void TCppInterOpInterpreter::CallFunc_SetFuncProto(CallFunc_t *func, ClassInfo_t *info,
                                                   const char *method, const char *proto,
                                                   Longptr_t *Offset,
                                                   ROOT::EFunctionMatchMode mode) const
{
   CallFunc_SetFuncProto(func, info, method, proto, false, Offset, mode);
}

void TCppInterOpInterpreter::CallFunc_SetFuncProto(CallFunc_t * /*func*/, ClassInfo_t * /*info*/,
                                                   const char * /*method*/,
                                                   const std::vector<TypeInfo_t *> & /*proto*/,
                                                   Longptr_t * /*Offset*/,
                                                   ROOT::EFunctionMatchMode /*mode*/) const
{
   rkUnsupported("CallFunc_SetFuncProto(std::vector<TypeInfo_t*>)");
}

void TCppInterOpInterpreter::CallFunc_SetFuncProto(CallFunc_t * /*func*/, ClassInfo_t * /*info*/,
                                                   const char * /*method*/,
                                                   const std::vector<TypeInfo_t *> & /*proto*/,
                                                   bool /*objectIsConst*/, Longptr_t * /*Offset*/,
                                                   ROOT::EFunctionMatchMode /*mode*/) const
{
   rkUnsupported("CallFunc_SetFuncProto(std::vector<TypeInfo_t*>, bool)");
}

////////////////////////////////////////////////////////////////////////////////
/// Does the interpreter know a class (or namespace) by this name?
///
/// ROOT asks this before building a TClass, e.g. when TH1::Fit resolves its
/// minimizer through the plugin manager. A real lookup in the interpreter is
/// the honest answer; kUnknown here means "not declared", which is exactly what
/// ROOT expects to act on.
///
/// kWithClassDefInline is never reported: detecting an inlined ClassDef needs
/// declaration inspection this adapter does not do, and claiming it would be a
/// guess. Under-reporting makes ROOT take its ordinary path.

TInterpreter::ECheckClassInfo TCppInterOpInterpreter::CheckClassInfo(const char *name,
                                                                    Bool_t /*autoload*/,
                                                                    Bool_t /*isClassOrNamespaceOnly*/)
{
   if (!name || !*name)
      return kUnknown;
   return Cpp::GetScopeFromCompleteName(name) ? kKnown : kUnknown;
}
