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

#include <set>
#include <string>
#include <unordered_map>
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

   // Fix 2 (M4b): TPluginManager::LoadHandlerMacros (TPluginManager.cxx:452)
   // calls gROOT->Macro(path,...), which calls this directly
   // (TROOT::Macro, TROOT.cxx:2497). Real ROOT (TCling::ExecuteMacro,
   // TCling.cxx:5521) delegates to TApplication::ExecuteFile's full
   // ACLiC/".x"/".X"-with-arguments metaprocessor -- deliberately not
   // reimplemented here (out of scope). This is the narrow slice that
   // shape actually needs: declare the *.C file's text (a plain top-level
   // function definition, ROOT's own ".X"-keep convention), then invoke the
   // no-arg function named after the file's own basename, mirroring what
   // cling's ".x"/".X" metacommand does for exactly that macro shape.
   Longptr_t ExecuteMacro(const char *filename, EErrorCode *error) override;

   // Fix 2 (M4b, discovered empirically): TPluginManager::AddHandler
   // (TPluginManager.cxx:568-579) calls this unconditionally whenever
   // TPH__IsReadingDirs() is true -- i.e. every single time a plugin handler
   // macro registers itself, which is exactly ExecuteMacro's call chain above.
   // ROOT's own base class already gives this a harmless inline default
   // (TInterpreter.h:259: `virtual const char *GetCurrentMacroName() const
   // {return nullptr;}`) precisely because tracking a macro-name stack is
   // optional bookkeeping, not a real reflection primitive -- but gen_fatal.py
   // does not know that and had generated a throwing override for it (every
   // non-pure virtual gets one unless named here), which meant every
   // TPluginHandler::AddHandler call from a macro threw mid-JIT and silently
   // aborted before fHandlers->Add(h) ever ran (verified with an instrumented
   // build: AddHandler's own post-call print never printed; the plugin's
   // TString origin field is display-only, never read by CheckNameMatch/
   // ExecPlugin). Matching ROOT's own documented default here, not fabricating
   // real macro-name tracking that nothing in this task's call chain needs.
   const char *GetCurrentMacroName() const override { return nullptr; }

   ECheckClassInfo CheckClassInfo(const char *name, Bool_t autoload,
                                  Bool_t isClassOrNamespaceOnly) override;

   // Family A (genuine): give cl a real ClassInfo_t, mirroring
   // TCling::SetClassInfo (TCling.cxx:4154-4269). Writing cl->fClassInfo is
   // legal because TClass.h now friends this class too (see the TClass.h hunk
   // appended to wasm/gates/p0deps/xbuild/host-rootcling.patch). Falls back to
   // ROOT's own "no info available" outcome (TClass.cxx:1486-1487) when the
   // interpreter genuinely does not know the class.
   void SetClassInfo(TClass *cl, Bool_t reload = kFALSE, Bool_t silent = kFALSE) override;

   // Genuinely truthful state, not S0 measurement: TClass::GetClass
   // (core/meta/src/TClass.cxx:3076-3083) reads/sets this flag through the
   // TInterpreter::SuspendAutoParsing RAII fence. A plain bool answers both
   // ends of the contract honestly -- no autoloading/reflection is involved.
   Bool_t SetSuspendAutoParsing(Bool_t value) override;
   Bool_t IsAutoParsingSuspended() const override;

   // Family 0: parse the header(s) a class needs, on demand, using the same
   // classname -> header-list table ROOT's own generated dictionaries hand to
   // RegisterModule (TCling.cxx:2275-2313). TClass::GetClass calls this right
   // after the SuspendAutoParsing fence above (TClass.cxx:3076-3083).
   Int_t AutoParse(const char *cls) override;

   ClassInfo_t *ClassInfo_Factory(Bool_t all) const override;
   ClassInfo_t *ClassInfo_Factory(ClassInfo_t *cl) const override;
   ClassInfo_t *ClassInfo_Factory(const char *name) const override;
   ClassInfo_t *ClassInfo_Factory(DeclId_t declid) const override;
   void ClassInfo_Init(ClassInfo_t *info, const char *name) const override;
   void ClassInfo_Delete(ClassInfo_t *info) const override;
   Bool_t ClassInfo_IsValid(ClassInfo_t *info) const override;
   const char *ClassInfo_Title(ClassInfo_t *info) const override;
   // Fix 3 (M4b, discovered empirically): TClass::GetClass(ClassInfo_t*, Bool_t)
   // (TClass.cxx:3425) calls this to look up the TClass by name for a
   // ClassInfo_t handle -- the exact path TBaseClass::GetClassPointer()
   // (TBaseClass.cxx:65) takes for a base class. Genuine via
   // Cpp::GetQualifiedName, same convention as BaseClassInfo_FullName below.
   const char *ClassInfo_FullName(ClassInfo_t *info) const override;
   // Discovered mid-M4b (not in the original family list): TListOfFunctions::Get
   // (core/meta/src/TListOfFunctions.cxx:320-324), the method-lookup path
   // TClass::GetMethodWithPrototype actually goes through, checks this before
   // building a TMethod at all. Genuine (if narrower than TCling's own
   // transparent-context walk): Cpp::GetParentScope's canonical-decl identity,
   // the same round-trip identity this file already relies on for
   // ClassInfo_t/DeclId_t (see GetDeclId(ClassInfo_t*) above).
   Bool_t ClassInfo_Contains(ClassInfo_t *info, DeclId_t declid) const override;
   // Family A: the DeclId_t <-> ClassInfo_t round trip SetClassInfo needs to
   // register a class with TClass::AddClassToDeclIdMap (TClass.h:597).
   // GetDeclId has 6 overloads in TInterpreter.h (CallFunc_t, ClassInfo_t,
   // DataMemberInfo_t, FuncTempInfo_t, MethodInfo_t, TypedefInfo_t); only the
   // ClassInfo_t one is genuinely implemented here -- the other 5 belong to the
   // MethodInfo_t/DataMemberInfo_t/CallFunc_t overload-resolution families this
   // task is scoped to avoid, so they are declared explicitly as loud overrides
   // rather than left to gen_fatal.py (whose overload-coverage check requires
   // every sibling overload of an implemented name to be declared by hand once
   // the name is in implemented.txt at all).
   DeclId_t GetDeclId(ClassInfo_t *info) const override;
   DeclId_t GetDeclId(CallFunc_t *) const override { rkUnsupported("GetDeclId(CallFunc_t*)"); }
   DeclId_t GetDeclId(DataMemberInfo_t *) const override { rkUnsupported("GetDeclId(DataMemberInfo_t*)"); }
   DeclId_t GetDeclId(FuncTempInfo_t *) const override { rkUnsupported("GetDeclId(FuncTempInfo_t*)"); }
   DeclId_t GetDeclId(MethodInfo_t *) const override { rkUnsupported("GetDeclId(MethodInfo_t*)"); }
   DeclId_t GetDeclId(TypedefInfo_t *) const override { rkUnsupported("GetDeclId(TypedefInfo_t*)"); }
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

   // Family F (narrow): populate a CallFunc_t directly from an already-resolved
   // MethodInfo_t handle -- what TMethodCall::Init(const TFunction*)
   // (TMethodCall.cxx:246) uses instead of re-resolving by name+prototype.
   void CallFunc_SetFunc(CallFunc_t *func, MethodInfo_t *info) const override;
   // Unsupported siblings of the name above (params-string calling convention;
   // a different, larger family -- see CallFunc_SetFuncProto's own stub note).
   void CallFunc_SetFunc(CallFunc_t *, ClassInfo_t *, const char *, const char *, bool,
                         Longptr_t *) const override
   {
      rkUnsupported("CallFunc_SetFunc(params-string, objectIsConst)");
   }
   void CallFunc_SetFunc(CallFunc_t *, ClassInfo_t *, const char *, const char *,
                         Longptr_t *) const override
   {
      rkUnsupported("CallFunc_SetFunc(params-string)");
   }
   // Family F: the actual execution primitive TMethodCall::Execute(objAddress,
   // args, nargs, ret) (TMethodCall.cxx:551-557) calls. Constructors go through
   // Cpp::MakeFunctionCallable's JitCall::InvokeConstructor; see the .cxx.
   void CallFunc_ExecWithArgsAndReturn(CallFunc_t *func, void *address, const void *args[] = nullptr,
                                       int nargs = 0, void *ret = nullptr) const override;

   // Family B (genuine): one scope's methods, enumerated once via
   // Cpp::GetClassMethods and cached in a tagged RkMethodInfo handle, or a
   // single method wrapped directly from a DeclId_t (same cast-soundness as
   // ClassInfo_Factory(DeclId_t) above).
   MethodInfo_t *MethodInfo_Factory(ClassInfo_t *clinfo) const override;
   MethodInfo_t *MethodInfo_Factory(DeclId_t declid) const override;
   MethodInfo_t *MethodInfo_Factory() const override { rkUnsupported("MethodInfo_Factory()"); }
   int MethodInfo_Next(MethodInfo_t *minfo) const override;
   Bool_t MethodInfo_IsValid(MethodInfo_t *minfo) const override;
   void MethodInfo_Delete(MethodInfo_t *minfo) const override;
   MethodInfo_t *MethodInfo_FactoryCopy(MethodInfo_t *minfo) const override;
   const char *MethodInfo_Name(MethodInfo_t *minfo) const override;
   // No reverse "mangled name from a decl" accessor exists in CppInterOp 1.9's
   // public API (GetFunctionAddress(const char*) takes one as *input* only;
   // grepped the whole header, see STATE.md fact 22). Confirmed by direct read
   // of TFunction.cxx:44 to be reached unconditionally by TFunction's own
   // constructor (a call site the task brief did not cite -- see STATE.md) --
   // left loud deliberately rather than fabricated.

   // Family C (genuine, narrowed like ClassInfo_Title): access-and-modifier
   // bits via CppInterOp's per-predicate accessors, OR'd into ROOT's own
   // EProperty bits (TDictionary.h) -- not the fuller clang-AST introspection
   // TClingMethodInfo::Property/ExtraProperty do (TClingMethodInfo.cxx:436-548).
   Long_t MethodInfo_Property(MethodInfo_t *minfo) const override;
   Long_t MethodInfo_ExtraProperty(MethodInfo_t *minfo) const override;
   int MethodInfo_NArg(MethodInfo_t *minfo) const override;
   int MethodInfo_NDefaultArg(MethodInfo_t *minfo) const override;
   // Same Cpp::GetDoxygenComment convention as ClassInfo_Title -- required by
   // TFunction's constructor (TFunction.cxx:43) alongside MethodInfo_Name.
   const char *MethodInfo_Title(MethodInfo_t *minfo) const override;

   // Family D (genuine; required for TPluginHandler::CheckNameMatch,
   // TPluginManager.cxx:179-191 -- see GetFunctionArgType/GetTypeAsString use
   // in the .cxx for MethodArgInfo_TypeNormalizedName, the critical one).
   MethodArgInfo_t *MethodArgInfo_Factory(MethodInfo_t *minfo) const override;
   MethodArgInfo_t *MethodArgInfo_Factory() const override { rkUnsupported("MethodArgInfo_Factory()"); }
   MethodArgInfo_t *MethodArgInfo_FactoryCopy(MethodArgInfo_t *marginfo) const override;
   void MethodArgInfo_Delete(MethodArgInfo_t *marginfo) const override;
   int MethodArgInfo_Next(MethodArgInfo_t *marginfo) const override;
   Bool_t MethodArgInfo_IsValid(MethodArgInfo_t *marginfo) const override;
   const char *MethodArgInfo_Name(MethodArgInfo_t *marginfo) const override;
   const char *MethodArgInfo_TypeName(MethodArgInfo_t *marginfo) const override;
   std::string MethodArgInfo_TypeNormalizedName(MethodArgInfo_t *marginfo) const override;
   const char *MethodArgInfo_DefaultValue(MethodArgInfo_t *marginfo) const override;
   Long_t MethodArgInfo_Property(MethodArgInfo_t *marginfo) const override;

   // Family E (genuine): real overload resolution, replacing the name-only
   // stub. TClass::GetMethodWithPrototype (TClass.cxx:4524) is the caller.
   DeclId_t GetFunctionWithPrototype(ClassInfo_t *cl, const char *method, const char *proto,
                                     Bool_t objectIsConst = kFALSE,
                                     ROOT::EFunctionMatchMode mode = ROOT::kConversionMatch) override;

   // Fix 3 (M4b): TClass::GetListOfBases (TClass.cxx:3721) calls
   // gInterpreter->CreateListOfBaseClasses(this) whenever cl->fBase is still
   // null and a real ClassInfo_t exists. Genuine, narrow (single non-virtual
   // public base -- Minuit2Minimizer's actual shape, verified via
   // Cpp::GetNumBases): walk Cpp::GetNumBases/Cpp::GetBaseClass once (mirrors
   // TCling::CreateListOfBaseClasses's own `TClingBaseClassInfo t(...); while
   // (t.Next()) ...` loop) and build one TBaseClass per base. Writing
   // cl->fBase is legal via the same TClass.h friend patch Family A already
   // needed for fClassInfo (host-rootcling.patch).
   void CreateListOfBaseClasses(TClass *cl) const override;

   // BaseClassInfo interface (Fix 3): only what TBaseClass's own ctor/
   // GetDelta() call unconditionally on this exact single-base shape --
   // TBaseClass.cxx:39 (FullName, in the ctor), :65 (ClassInfo, pure virtual
   // in the base so it must exist regardless), :83 (Offset, for GetDelta()).
   // Genuine via Cpp::GetNumBases/GetBaseClass/GetBaseClassOffset -- real
   // CppInterOp primitives, not fabricated numbers.
   BaseClassInfo_t *BaseClassInfo_Factory(ClassInfo_t *info) const override;
   int BaseClassInfo_Next(BaseClassInfo_t *bcinfo) const override;
   void BaseClassInfo_Delete(BaseClassInfo_t *bcinfo) const override;
   ClassInfo_t *BaseClassInfo_ClassInfo(BaseClassInfo_t *bcinfo) const override;
   const char *BaseClassInfo_FullName(BaseClassInfo_t *bcinfo) const override;
   Longptr_t BaseClassInfo_Offset(BaseClassInfo_t *bcinfo, void *address = nullptr,
                                  bool isderived = true) const override;
   // Unsupported siblings of the two overloaded names above (a direct-base-
   // pointing factory that skips enumeration entirely, and an onlyDirect
   // iteration mode) -- TCling::CreateListOfBaseClasses's own iteration idiom
   // uses neither, and CppInterOp's GetNumBases/GetBaseClass only exposes
   // direct bases in the first place, so onlyDirect has no different behavior
   // to give it here.
   BaseClassInfo_t *BaseClassInfo_Factory(ClassInfo_t *, ClassInfo_t *) const override
   {
      rkUnsupported("BaseClassInfo_Factory(derived, base)");
   }
   int BaseClassInfo_Next(BaseClassInfo_t *, int) const override
   {
      rkUnsupported("BaseClassInfo_Next(onlyDirect)");
   }
   // BaseClassInfo_Property/_TmpltName/_Name/_Tagnum are deliberately left to
   // gen_fatal.py's loud default: CppInterOp 1.9 exposes no per-base access-
   // specifier or virtual-base predicate at all (grepped the whole header --
   // only GetNumBases/GetBaseClass/GetBaseClassOffset exist), so a real access
   // bit cannot be computed without guessing, which the project rules forbid
   // more strongly than an unimplemented stub. None of these four are called
   // by TBaseClass's ctor or by GetDelta(); if some other caller reaches them,
   // the loud failure is the correct, honest answer.

#include "fatal_methods.inc"

private:
   void *fInterp = nullptr;   ///< the kernel's clang-repl, borrowed, never owned
   std::vector<Module> fModules;
   bool fAutoParsingSuspended = false;

   // Family 0: classname -> candidate header list, accumulated across every
   // RegisterModule call exactly as TCling::RegisterModule builds
   // fClassesHeadersMap (TCling.cxx:2275-2313), except keyed by name directly
   // instead of by a hash (this adapter has no need for TCling's hash-collision
   // bookkeeping). AutoParse consults it; fAutoParsedHeaders is the per-session
   // "already declared" set so re-asking for the same class does not re-#include
   // its header.
   std::unordered_map<std::string, std::vector<std::string>> fClassesHeadersMap;
   std::set<std::string> fAutoParsedHeaders;
};

#endif
