# Generate RConfigure.h from ROOT's own template for the isolated G2 profile.
# This is intentionally not a substitute ROOT header: it invokes CMake's
# configure_file on config/RConfigure.in from the sha256-verified ROOT source.
cmake_minimum_required(VERSION 3.20)

foreach(required ROOT_SOURCE OUTPUT_HEADER CXX)
  if(NOT DEFINED ${required})
    message(FATAL_ERROR "-D${required}=... is required")
  endif()
endforeach()
if(DEFINED OUTPUT_OPTIONS_HEADER)
  set(options_template "${ROOT_SOURCE}/config/RConfigOptions.in")
  if(NOT EXISTS "${options_template}")
    message(FATAL_ERROR "ROOT RConfigOptions template not found: ${options_template}")
  endif()
endif()
set(template "${ROOT_SOURCE}/config/RConfigure.in")
if(NOT EXISTS "${template}")
  message(FATAL_ERROR "ROOT RConfigure template not found: ${template}")
endif()

# These are ROOT's RootConfiguration.cmake probes, run for the actual compiler.
execute_process(
  COMMAND "${CXX}" -std=c++17 -dM -E -x c++ /dev/null
  RESULT_VARIABLE cxx_probe_status OUTPUT_VARIABLE cxx_macros ERROR_VARIABLE cxx_probe_error)
if(NOT cxx_probe_status EQUAL 0)
  message(FATAL_ERROR "could not query ${CXX}: ${cxx_probe_error}")
endif()
string(REGEX MATCH "__cplusplus[ 	]+([0-9]+)" cxx_match "${cxx_macros}")
if(NOT CMAKE_MATCH_1)
  message(FATAL_ERROR "${CXX} did not report __cplusplus")
endif()
set(__cplusplus "${CMAKE_MATCH_1}L")

set(attribute_probe "${OUTPUT_HEADER}.attribute-probe.cxx")
file(WRITE "${attribute_probe}" "inline __attribute__((always_inline)) bool f(unsigned long x) { return x != 0; }\nint main() { return f(0); }\n")
execute_process(COMMAND "${CXX}" -std=c++17 -c "${attribute_probe}" -o "${attribute_probe}.o"
  RESULT_VARIABLE attribute_probe_status ERROR_VARIABLE attribute_probe_error)
if(attribute_probe_status EQUAL 0)
  set(has_found_attribute_always_inline define)
else()
  set(has_found_attribute_always_inline undef)
endif()

file(WRITE "${attribute_probe}" "inline __attribute__((noinline)) bool f(unsigned long x) { return x != 0; }\nint main() { return f(0); }\n")
execute_process(COMMAND "${CXX}" -std=c++17 -c "${attribute_probe}" -o "${attribute_probe}.o"
  RESULT_VARIABLE attribute_probe_status ERROR_VARIABLE attribute_probe_error)
if(attribute_probe_status EQUAL 0)
  set(has_found_attribute_noinline define)
else()
  set(has_found_attribute_noinline undef)
endif()

# RootConfiguration.cmake sets these from enabled ROOT components. G2 links no
# ROOT component, so the only truthful profile is that all optional components
# are absent. The template still owns the emitted header and macro spelling.
foreach(feature IN ITEMS
    setresuid hasmathmore haspthread hasxft hasclad hascocoa hasvdt
    hasstdexperimentalsimd experimentalsimdpinavxabi usecxxmodules
    useimt memory_term hascefweb hasqt6webengine hasdavix hascurl hasdataframe
    hasroot7 use_less_includes usezlibng hastmvacpu hastmvagpu hastmvacudnn
    haspymva hasrmva hasuring hasgeom)
  set(${feature} undef)
endforeach()
set(uselibc++ undef)

# RootConfiguration.cmake falls back to 64 while cross compiling. The remaining
# path variables are inert because this non-installed header omits R__HAVE_CONFIG.
set(architecture "emscripten-header-only")
set(hardwareinterferencesize 64)
set(prefix "")
set(bindir "")
set(libdir "")
set(etcdir "")
set(datadir "")
set(docdir "")
set(macrodir "")
set(tutdir "")
set(srcdir "")
set(iconpath "")
set(ttffontdir "")
set(extraiconpath "")
set(configoptions "")
set(configfeatures "")
configure_file("${template}" "${OUTPUT_HEADER}" NEWLINE_STYLE UNIX)
if(DEFINED OUTPUT_OPTIONS_HEADER)
  configure_file("${options_template}" "${OUTPUT_OPTIONS_HEADER}" NEWLINE_STYLE UNIX)
endif()
