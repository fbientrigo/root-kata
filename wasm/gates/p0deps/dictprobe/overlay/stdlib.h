/* Dictionary-generator-only overlay (never used by em++). Cling's interpreter prelude
   declares at_quick_exit with the glibc 'throw()' spec (Interpreter.cpp:455-506), which
   conflicts with musl's plain declaration. Hide musl's redeclaration from the parser;
   ::at_quick_exit stays visible through cling's own prelude declaration. */
#define at_quick_exit __rootwasm_dictgen_musl_at_quick_exit
#include_next <stdlib.h>
#undef at_quick_exit
