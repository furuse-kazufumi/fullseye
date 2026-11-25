cmake_minimum_required(VERSION 3.21)
project(FullseyeConsumer LANGUAGES CXX)

find_package(Fullseye 0 CONFIG REQUIRED)
add_executable(fullseye_consumer main.cpp)
target_link_libraries(fullseye_consumer PRIVATE Fullseye::CXX)
