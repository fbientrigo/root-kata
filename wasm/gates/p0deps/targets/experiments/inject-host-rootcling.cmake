# Runs right after project(ROOT) via CMAKE_PROJECT_ROOT_INCLUDE. Pre-declares the two
# rootcling targets as IMPORTED host executables so $<TARGET_FILE:...> in
# RootMacros.cmake:643-677 would resolve to host binaries. Configure-only probe.
add_executable(rootcling_stage1 IMPORTED GLOBAL)
set_target_properties(rootcling_stage1 PROPERTIES IMPORTED_LOCATION /nonexistent/host/rootcling_stage1)
add_executable(rootcling IMPORTED GLOBAL)
set_target_properties(rootcling PROPERTIES IMPORTED_LOCATION /home/fabian/thesis/FairShip/.pixi/envs/default/bin/rootcling)
message(STATUS "P0-PROBE: injected IMPORTED rootcling_stage1 + rootcling")
