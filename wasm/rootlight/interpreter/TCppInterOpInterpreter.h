// ROOT's TInterpreter, implemented over CppInterOp/clang-repl for WebAssembly.
//
// ROOT loads its interpreter as a plugin: TROOT::InitInterpreter
// (core/base/src/TROOT.cxx:2223-2262) looks up "CreateInterpreter" and
// "DestroyInterpreter" and calls them. This class is what the first one returns,
// so TROOT, TH1, TFormula, TClass and the plugin manager stay untouched.
//
// It does NOT create a compiler. The browser kernel (xeus-cpp-lite) already owns
// a clang-repl instance; this adapter attaches to it through
// Cpp::GetInterpreter(). Creating a second clang in the same wasm process is
// explicitly out of bounds.
//
// Rule for every service in here: implement it genuinely, or fail loudly.
// Returning a plausible default (no such class, empty list, zero) would be the
// silent no-op the project rules forbid -- it would make ROOT quietly wrong
// instead of visibly unfinished. See gen_fatal.py.
#ifndef ROOT_TCppInterOpInterpreter
#define ROOT_TCppInterOpInterpreter

#include <string>
#include <vector>

#include "TInterpreter.h"

/// Fail loudly, and never return a value the caller could mistake for an answer.
///
/// Not exit(): in this environment exit() traps inside Emscripten's atexit
/// dispatch and discards everything the kernel captured for the cell, so the
/// message would be lost (wasm/gates/rootweb/FINDINGS.md). A C++ exception
/// reaches the user with its text intact and kills only the current cell.
[[noreturn]] void rkUnsupported(const char *service);

class TCppInterOpInterpreter : public TInterpreter {
public:
   /// One ROOT dictionary, as handed to us by its generated registration code.
   struct Module {
      std::string fName;
      std::vector<std::string> fHeaders;
   };

   TCppInterOpInterpreter(const char *name, const char *title);

   void Initialize() override;
   void ShutDown() override;

   void RegisterModule(const char *modulename, const char **headers, const char **includePaths,
                       const char *payloadCode, const char *fwdDeclsCode, void (*triggerFunc)(),
                       const FwdDeclArgsToKeepCollection_t &fwdDeclArgsToKeep,
                       const char **classesHeaders, Bool_t lateRegistration,
                       Bool_t hasCxxModule) override;

   /// Dictionaries registered so far, in registration order. Diagnostics only.
   const std::vector<Module> &RegisteredModules() const { return fModules; }

   // --- M4: compiling and calling a TFormula -------------------------------
   // TFormula::InputFormulaIntoCling (hist/hist/src/TFormula.cxx:944-961) feeds
   // its generated C++ through ProcessLine and Declare, then TMethodCall
   // (core/meta/src/TMethodCall.cxx:184-350) resolves it and asks for a callable
   // pointer. These are the members of that path.
   Bool_t Declare(const char *code) override;
   Longptr_t ProcessLine(const char *line, EErrorCode *error) override;
   Longptr_t ProcessLineSynch(const char *line, EErrorCode *error) override;
   Longptr_t Calc(const char *line, EErrorCode *error) override;

   ECheckClassInfo CheckClassInfo(const char *name, Bool_t autoload,
                                  Bool_t isClassOrNamespaceOnly) override;

   ClassInfo_t *ClassInfo_Factory(Bool_t all) const override;
   ClassInfo_t *ClassInfo_Factory(ClassInfo_t *cl) const override;
   ClassInfo_t *ClassInfo_Factory(const char *name) const override;
   ClassInfo_t *ClassInfo_Factory(DeclId_t declid) const override;
   void ClassInfo_Init(ClassInfo_t *info, const char *name) const override;
   void ClassInfo_Delete(ClassInfo_t *info) const override;
   Bool_t ClassInfo_IsValid(ClassInfo_t *info) const override;
   // Overloads of the names above that this adapter does NOT support. They are
   // spelled out rather than left to ROOT's base class, whose inline defaults
   // would silently do nothing.
   void ClassInfo_Init(ClassInfo_t *, int) const override { rkUnsupported("ClassInfo_Init(tagnum)"); }
   void ClassInfo_Delete(ClassInfo_t *, void *) const override { rkUnsupported("ClassInfo_Delete(arena)"); }

   CallFunc_t *CallFunc_Factory() const override;
   void CallFunc_Init(CallFunc_t *func) const override;
   void CallFunc_Delete(CallFunc_t *func) const override;
   Bool_t CallFunc_IsValid(CallFunc_t *func) const override;
   CallFuncIFacePtr_t CallFunc_IFacePtr(CallFunc_t *func) const override;
   void CallFunc_SetFuncProto(CallFunc_t *func, ClassInfo_t *info, const char *method,
                              const char *proto, Longptr_t *Offset,
                              ROOT::EFunctionMatchMode mode) const override;
   void CallFunc_SetFuncProto(CallFunc_t *func, ClassInfo_t *info, const char *method,
                              const char *proto, bool objectIsConst, Longptr_t *Offset,
                              ROOT::EFunctionMatchMode mode) const override;
   void CallFunc_SetFuncProto(CallFunc_t *func, ClassInfo_t *info, const char *method,
                              const std::vector<TypeInfo_t *> &proto, Longptr_t *Offset,
                              ROOT::EFunctionMatchMode mode) const override;
   void CallFunc_SetFuncProto(CallFunc_t *func, ClassInfo_t *info, const char *method,
                              const std::vector<TypeInfo_t *> &proto, bool objectIsConst,
                              Longptr_t *Offset, ROOT::EFunctionMatchMode mode) const override;

#include "fatal_methods.inc"

private:
   void *fInterp = nullptr;   ///< the kernel's clang-repl, borrowed, never owned
   std::vector<Module> fModules;
};

#endif
