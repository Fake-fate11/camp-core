cmake_minimum_required(VERSION 3.16)
project(camp_online LANGUAGES CXX)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
include(CTest)

option(CAMP_AUTOWARE_MAP_BRIDGE "Build the optional Lanelet2/RouteHandler bridge" OFF)
option(CAMP_AUTOWARE_MAP_EXAMPLE "Build the official Lanelet2 map bridge and offline example" OFF)
if(CAMP_AUTOWARE_MAP_EXAMPLE)
  set(CAMP_AUTOWARE_MAP_BRIDGE ON)
endif()

find_package(nlohmann_json REQUIRED)
add_library(camp_online src/selector.cpp)
add_library(camp::camp_online ALIAS camp_online)
target_compile_features(camp_online PUBLIC cxx_std_17)
target_include_directories(camp_online PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
target_link_libraries(camp_online PRIVATE nlohmann_json::nlohmann_json)
add_executable(camp_score examples/score.cpp)
target_link_libraries(camp_score PRIVATE camp_online nlohmann_json::nlohmann_json)

set(camp_package_dir ${CMAKE_INSTALL_LIBDIR}/cmake/camp_online)
install(TARGETS camp_online EXPORT camp_onlineTargets
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(FILES include/camp/selector.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/camp)
install(EXPORT camp_onlineTargets NAMESPACE camp:: DESTINATION ${camp_package_dir})

# Keep the map target in its own export set. A scorer-only installed consumer
# must not acquire ROS dependencies merely because this build included the bridge.
set(CAMP_LANELET_DEPENDENCIES
  autoware_planning_msgs
  autoware_route_handler
  lanelet2_core
  lanelet2_routing
  lanelet2_traffic_rules)
if(CAMP_AUTOWARE_MAP_BRIDGE)
  find_package(ament_cmake REQUIRED)
  foreach(dep IN LISTS CAMP_LANELET_DEPENDENCIES)
    find_package(${dep} REQUIRED)
  endforeach()
  add_library(camp_lanelet_context src/lanelet_context.cpp)
  add_library(camp::camp_lanelet_context ALIAS camp_lanelet_context)
  target_include_directories(camp_lanelet_context PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)
  target_compile_features(camp_lanelet_context PUBLIC cxx_std_17)
  target_link_libraries(camp_lanelet_context nlohmann_json::nlohmann_json)
  ament_target_dependencies(camp_lanelet_context ${CAMP_LANELET_DEPENDENCIES})
  install(TARGETS camp_lanelet_context EXPORT camp_lanelet_contextTargets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
  install(FILES include/camp/lanelet_context.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/camp)
  install(EXPORT camp_lanelet_contextTargets NAMESPACE camp:: DESTINATION ${camp_package_dir})
endif()

if(CAMP_AUTOWARE_MAP_EXAMPLE)
  set(camp_map_example_dependencies
    autoware_geography_utils
    autoware_map_projection_loader
    autoware_lanelet2_extension
    autoware_lanelet2_utils
    lanelet2_io
    autoware_map_msgs)
  foreach(dep IN LISTS camp_map_example_dependencies)
    find_package(${dep} REQUIRED)
  endforeach()
  add_executable(camp_export_map examples/export_map.cpp)
  target_link_libraries(camp_export_map camp_lanelet_context)
  ament_target_dependencies(camp_export_map ${camp_map_example_dependencies})
endif()

configure_package_config_file(camp_onlineConfig.cmake.in
  ${CMAKE_CURRENT_BINARY_DIR}/camp_onlineConfig.cmake
  INSTALL_DESTINATION ${camp_package_dir})
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/camp_onlineConfig.cmake DESTINATION ${camp_package_dir})

if(BUILD_TESTING)
  add_executable(camp_selector_tests tests/selector_test.cpp)
  target_link_libraries(camp_selector_tests PRIVATE camp_online nlohmann_json::nlohmann_json)
  foreach(case fixed scene status stable_ties candidate_pool_k invalid_inputs reset masked_mean)
    add_test(NAME camp_selector_${case}
      COMMAND camp_selector_tests ${case} ${CMAKE_CURRENT_BINARY_DIR}/test_models/${case})
  endforeach()
endif()
