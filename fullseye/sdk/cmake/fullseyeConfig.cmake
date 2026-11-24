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
# Make an ASCII-only C++ literal from the runtime root's UTF-8 bytes. Adjacent
# literals terminate every \\x escape, including before an ASCII hex digit.
# runtime root の UTF-8 byte 列を ASCII だけの C++ 文字列にし、隣接 literal
# で各 \\x escape を終端する。
function(_fullseye_utf8_cxx_literal value out)
  string(HEX "${value}" _fullseye_runtime_root_hex)
  string(REGEX MATCHALL ".." _fullseye_runtime_root_bytes "${_fullseye_runtime_root_hex}")
  set(_fullseye_runtime_root_literal "")
  foreach(_fullseye_byte IN LISTS _fullseye_runtime_root_bytes)
    string(APPEND _fullseye_runtime_root_literal "\\x${_fullseye_byte}\"\"")
  endforeach()
  set(${out} "${_fullseye_runtime_root_literal}" PARENT_SCOPE)
endfunction()
_fullseye_utf8_cxx_literal("${fullseye_PYTHON_RUNTIME_ROOT}" _fullseye_runtime_root_for_cpp)
get_filename_component(_fullseye_python_home "${fullseye_PYTHON_EXECUTABLE}" DIRECTORY)
_fullseye_utf8_cxx_literal("${_fullseye_python_home}" _fullseye_python_home_for_cpp)
target_compile_definitions(fullseye_source_bridge PRIVATE
  FULLSEYE_BUILD
  PYBIND11_SIMPLE_GIL_MANAGEMENT
  "FULLSEYE_DEFAULT_RUNTIME_ROOT=\"${_fullseye_runtime_root_for_cpp}\""
  "FULLSEYE_DEFAULT_PYTHON_HOME=\"${_fullseye_python_home_for_cpp}\"")
target_include_directories(fullseye_source_bridge PUBLIC "${fullseye_SDK_INCLUDE_DIR}")
target_link_libraries(fullseye_source_bridge PRIVATE pybind11::embed)
if(MINGW)
  # Keep both the bridge and a C++ consumer independent of the compiler's
  # PATH. libwinpthread may remain dynamic, so stage it beside the app too.
  # bridge と C++ consumer を compiler の PATH から切り離す。
  target_link_options(fullseye_source_bridge PUBLIC -static-libgcc -static-libstdc++)
  get_filename_component(_fullseye_mingw_bin "${CMAKE_CXX_COMPILER}" DIRECTORY)
  get_filename_component(_fullseye_mingw_root "${_fullseye_mingw_bin}" DIRECTORY)
  file(GLOB _fullseye_winpthread "${_fullseye_mingw_root}/*/lib/libwinpthread.a")
  if(_fullseye_winpthread)
    target_link_libraries(fullseye_source_bridge PRIVATE "${_fullseye_winpthread}")
  endif()
  set(_fullseye_winpthread_dll "${_fullseye_mingw_root}/bin/libwinpthread-1.dll")
  if(EXISTS "${_fullseye_winpthread_dll}")
    add_custom_command(TARGET fullseye_source_bridge POST_BUILD
      COMMAND "${CMAKE_COMMAND}" -E copy_if_different
              "${_fullseye_winpthread_dll}" "$<TARGET_FILE_DIR:fullseye_source_bridge>")
  endif()
endif()
if(WIN32)
  # A C/C++ consumer normally has no Python directory on PATH. Deploy the
  # CPython DLL to CMake's runtime output directory, shared by the default
  # consumer executable and this bridge. / consumer 実行ファイルの横へ置く。
  get_filename_component(_fullseye_python_bin "${fullseye_PYTHON_EXECUTABLE}" DIRECTORY)
  set(_fullseye_python_runtime
      "${_fullseye_python_bin}/python${Python_VERSION_MAJOR}${Python_VERSION_MINOR}.dll")
  if(NOT EXISTS "${_fullseye_python_runtime}")
    message(FATAL_ERROR
      "Fullseye could not locate Python's runtime DLL next to ${fullseye_PYTHON_EXECUTABLE}")
  endif()
  add_custom_command(TARGET fullseye_source_bridge POST_BUILD
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different
            "${_fullseye_python_runtime}" "$<TARGET_FILE_DIR:fullseye_source_bridge>")
endif()
set_target_properties(fullseye_source_bridge PROPERTIES
  OUTPUT_NAME fullseye
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN YES)
