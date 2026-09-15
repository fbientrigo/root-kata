// LD_PRELOAD shim: log every dlopen/dlmopen; deny paths containing P0_DENY (e.g. libCling).
#define _GNU_SOURCE
#include <dlfcn.h>
#include <execinfo.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void *(*real_dlopen)(const char *, int);
static void *(*real_dlmopen)(Lmid_t, const char *, int);

static int handle(const char *fn, const char *path) {
  const char *deny = getenv("P0_DENY");
  int denied = deny && *deny && path && strstr(path, deny);
  fprintf(stderr, "[shim] %s(%s)%s\n", fn, path ? path : "NULL", denied ? " -> DENIED" : "");
  if (getenv("P0_BT_ALL") || (path && (strstr(path, "Cling") || denied))) {
    void *bt[32];
    int n = backtrace(bt, 32);
    fprintf(stderr, "[shim] backtrace for %s:\n", path);
    backtrace_symbols_fd(bt, n, 2);
  }
  return denied;
}

void *dlopen(const char *path, int flags) {
  if (!real_dlopen) real_dlopen = dlsym(RTLD_NEXT, "dlopen");
  if (handle("dlopen", path)) return real_dlopen("/p0-denied-by-shim/libCling.so", flags);  // NULL + real dlerror()
  return real_dlopen(path, flags);
}

void *dlmopen(Lmid_t lm, const char *path, int flags) {
  if (!real_dlmopen) real_dlmopen = dlsym(RTLD_NEXT, "dlmopen");
  if (handle("dlmopen", path)) return real_dlmopen(lm, "/p0-denied-by-shim/libCling.so", flags);
  return real_dlmopen(lm, path, flags);
}

// Run E: optionally short-circuit ROOT::Experimental::ObjectAutoRegistrationEnabled()
// (called cross-DSO from TH1::Build) so its gEnv->GetValue -> gROOT -> InitInterpreter
// path is skipped. P0_AUTOREG=1 returns true (ROOT 6 default), 0 returns false; unset forwards.
int _ZN4ROOT12Experimental29ObjectAutoRegistrationEnabledEv(void) {
  const char *v = getenv("P0_AUTOREG");
  if (v) {
    static int logged;
    if (!logged++) fprintf(stderr, "[shim] ObjectAutoRegistrationEnabled() short-circuited -> %d\n", atoi(v));
    return atoi(v) != 0;
  }
  static int (*real)(void);
  if (!real) real = dlsym(RTLD_NEXT, "_ZN4ROOT12Experimental29ObjectAutoRegistrationEnabledEv");
  return real();
}
