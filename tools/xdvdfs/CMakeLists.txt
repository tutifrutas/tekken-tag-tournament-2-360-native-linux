cmake_minimum_required(VERSION 3.20)

project(xdvdfs_tool)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(xdvdfs_tool
    main.cpp
    memory_mapped_file.cpp
)

option(TTT2_XDVDFS_TESTS "Build native extraction/mapping checks" OFF)
if(TTT2_XDVDFS_TESTS)
    enable_testing()
    add_executable(ttt2_mmap_test ../../tests/native/mmap_test.cpp memory_mapped_file.cpp)
    target_include_directories(ttt2_mmap_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
    add_test(NAME native_mmap COMMAND ttt2_mmap_test)
endif()

target_compile_options(xdvdfs_tool PRIVATE
    -Wall
    -Wextra
    -Wpedantic
)
