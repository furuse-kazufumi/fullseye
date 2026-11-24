# Fullseye source SDK consumer package / Fullseye ソース SDK 利用側パッケージ。
# This file is included through ``python -m fullseye.sdk --cmakedir``. The
# generated shim pins the Python interpreter and package root that requested
# it, so the bridge never guesses a global Python at runtime.
if(TARGET fullseye::fullseye)
  return()
endif()

foreach(_fullseye_required IN ITEMS fullseye_PYTHON_EXECUTABLE fullseye_PYTHON_RUNTIME_ROOT
                                      fullseye_SDK_SOURCE_FILE fullseye_SDK_INCLUDE_DIR)
  if(NOT DEFINED ${_fullseye_required} OR "${${_fullseye_required}}" STREQUAL "")
    message(FATAL_ERROR
      "Fullseye SDK must be located with: python -m fullseye.sdk --cmakedir\n"
      "Then pass -Dfullseye_DIR=that printed directory.")
  endif()
endforeach()

if(NOT EXISTS "${fullseye_SDK_SOURCE_FILE}" OR NOT EXISTS "${fullseye_SDK_INCLUDE_DIR}/fullseye.hpp")
  message(FATAL_ERROR "Fullseye SDK source payload is missing; reinstall fullseye.")
endif()

if(NOT CMAKE_CXX_COMPILER_LOADED)
  enable_language(CXX)
endif()
set(Python_EXECUTABLE "${fullseye_PYTHON_EXECUTABLE}")
find_package(Python 3.11 EXACT COMPONENTS Interpreter Development.Embed REQUIRED)

execute_process(
  COMMAND "${fullseye_PYTHON_EXECUTABLE}" -m pybind11 --cmakedir
  RESULT_VARIABLE _fullseye_pybind_status
  OUTPUT_VARIABLE pybind11_DIR
  ERROR_VARIABLE _fullseye_pybind_error
  OUTPUT_STRIP_TRAILING_WHITESPACE)
string(REGEX REPLACE "^\"(.*)\"$" "\\1" pybind11_DIR "${pybind11_DIR}")
if(NOT _fullseye_pybind_status EQUAL 0 OR "${pybind11_DIR}" STREQUAL "")
  message(FATAL_ERROR
    "Fullseye needs its installed pybind11 headers, but they are unavailable: ${_fullseye_pybind_error}")
endif()
find_package(pybind11 2.13.6 CONFIG REQUIRED
  PATHS "${pybind11_DIR}"
  NO_DEFAULT_PATH)

add_library(fullseye_source_bridge SHARED "${fullseye_SDK_SOURCE_FILE}")
add_library(fullseye::fullseye ALIAS fullseye_source_bridge)
target_compile_features(fullseye_source_bridge PUBLIC cxx_std_20)
file(TO_CMAKE_PATH "${fullseye_PYTHON_RUNTIME_ROOT}" _fullseye_runtime_root_for_cpp)
target_compile_definitions(fullseye_source_bridge PRIVATE
  FULLSEYE_BUILD
  PYBIND11_SIMPLE_GIL_MANAGEMENT
  "FULLSEYE_DEFAULT_RUNTIME_ROOT=\"${_fullseye_runtime_root_for_cpp}\"")
target_include_directories(fullseye_source_bridge PUBLIC "${fullseye_SDK_INCLUDE_DIR}")
target_link_libraries(fullseye_source_bridge PRIVATE pybind11::embed)
set_target_properties(fullseye_source_bridge PROPERTIES
  OUTPUT_NAME fullseye
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN YES)
