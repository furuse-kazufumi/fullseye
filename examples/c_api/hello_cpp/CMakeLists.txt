cmake_minimum_required(VERSION 3.21)
project(fullseye_hello_cpp LANGUAGES CXX)

find_package(fullseye CONFIG REQUIRED)
add_executable(app main.cpp)
target_link_libraries(app PRIVATE fullseye::fullseye)
fullseye_deploy_runtime(app)
