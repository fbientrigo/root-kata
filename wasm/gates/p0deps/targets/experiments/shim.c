#define _GNU_SOURCE
#include <dlfcn.h>
#include <execinfo.h>
#include <string.h>
#include <unistd.h>
void *dlopen(const char *f, int m) {
  static void *(*real)(const char *, int);
  if (!real) real = dlsym(RTLD_NEXT, "dlopen");
  if (f && strstr(f, "libCling")) { void *b[40]; int n = backtrace(b, 40); backtrace_symbols_fd(b, n, 2); }
  return real(f, m);
}
