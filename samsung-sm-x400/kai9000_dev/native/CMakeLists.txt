cmake_minimum_required(VERSION 3.22)
project(kai9000_native_probe LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(kai9000_native_probe src/kai_probe.cpp)

target_compile_options(kai9000_native_probe PRIVATE -Wall -Wextra -Wpedantic)
