cmake_minimum_required(VERSION 3.21)
project(fullseye_hello_c LANGUAGES C)

find_package(fullseye CONFIG REQUIRED)
add_executable(app hello.c)
target_link_libraries(app PRIVATE fullseye::fullseye)
set_property(TARGET app PROPERTY C_STANDARD 11)
fullseye_deploy_runtime(app)
