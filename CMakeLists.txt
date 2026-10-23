cmake_minimum_required(VERSION 3.25)
project(ttt2 LANGUAGES CXX)
if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    message(FATAL_ERROR "This project targets native Linux.")
endif()
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()
enable_testing()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_test(NAME native_data_preparation COMMAND "${Python3_EXECUTABLE}"
    "${CMAKE_CURRENT_SOURCE_DIR}/tests/native/test_data_preparation.py")
# The independent tekken-360-kde-launcher repository owns the launcher UI.
set(REXSDK_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../rexglue-sdk" CACHE PATH "Checkout of https://github.com/tutifrutas/rexglue-sdk")
set(REXGLUE_USE_D3D12 OFF CACHE BOOL "Disable Direct3D host backend")
set(REXGLUE_USE_VULKAN ON CACHE BOOL "Native Vulkan backend")
include(generated/rexglue.cmake)
add_executable(ttt2 src/main.cpp)
rexglue_setup_target(ttt2 GPU_PLUGINS xenos)
set_property(TARGET ttt2 APPEND PROPERTY BUILD_RPATH "$ORIGIN")
add_custom_target(ttt2_stage_gpu_plugin
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different
        "$<TARGET_FILE:rexgpu-xenos>"
        "${CMAKE_CURRENT_BINARY_DIR}/$<TARGET_FILE_NAME:rexgpu-xenos>"
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different
        "$<TARGET_FILE:rexruntime>"
        "${CMAKE_CURRENT_BINARY_DIR}/$<TARGET_FILE_NAME:rexruntime>"
    DEPENDS rexgpu-xenos rexruntime VERBATIM)
add_dependencies(ttt2 ttt2_stage_gpu_plugin)
