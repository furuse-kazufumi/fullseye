cmake_minimum_required(VERSION 3.21)
project(fullseye_hello_pipeline LANGUAGES CXX)

find_package(fullseye CONFIG REQUIRED)
add_executable(app main.cpp)
target_link_libraries(app PRIVATE fullseye::fullseye)
configure_file(inspect.json inspect.json COPYONLY)
fullseye_deploy_runtime(app)
