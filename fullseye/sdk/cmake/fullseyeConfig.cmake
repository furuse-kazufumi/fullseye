# Fullseye source SDK consumer package / Fullseye ソース SDK 利用側パッケージ。
# This file is included through ``python -m fullseye.sdk --cmakedir``. The
# generated shim records the Python interpreter and package root that requested
# it.  The bridge writes those facts to a runtime manifest beside each executable
# instead of baking a venv path into a DLL.
if(TARGET fullseye::fullseye)
  return()
endif()

foreach(_fullseye_required IN ITEMS fullseye_PYTHON_EXECUTABLE fullseye_PYTHON_RUNTIME_ROOT
                                      fullseye_PYTHON_HOME fullseye_SDK_ABI_VERSION fullseye_SDK_SOURCE_FILE
                                      fullseye_SDK_INCLUDE_DIR)
  if(NOT DEFINED ${_fullseye_required} OR "${${_fullseye_required}}" STREQUAL "")
    message(FATAL_ERROR
      "Fullseye SDK must be located with: python -m fullseye.sdk --cmakedir\n"
      "Then pass -Dfullseye_DIR=that printed directory.")
  endif()
endforeach()

if(NOT EXISTS "${fullseye_SDK_SOURCE_FILE}" OR NOT EXISTS "${fullseye_SDK_INCLUDE_DIR}/fullseye.hpp")
  message(FATAL_ERROR "Fullseye SDK source payload is missing; reinstall fullseye.")
endif()

include(CheckLanguage)
check_language(CXX)
if(NOT CMAKE_CXX_COMPILER)
  message(FATAL_ERROR
    "Fullseye cannot configure because no C++ compiler was found.\n"
    "Windows: winget install Microsoft.VisualStudio.2022.BuildTools\n"
    "Linux:   sudo apt-get install build-essential\n"
    "macOS:   xcode-select --install")
endif()
if(NOT CMAKE_CXX_COMPILER_LOADED)
  enable_language(CXX)
endif()
set(Python_EXECUTABLE "${fullseye_PYTHON_EXECUTABLE}")
find_package(Python 3.11 EXACT COMPONENTS Interpreter Development.Embed QUIET)
if(NOT Python_Interpreter_FOUND OR NOT Python_Development.Embed_FOUND)
  message(FATAL_ERROR
    "Fullseye needs Python 3.11 development headers (Python.h) for the selected interpreter:\n"
    "  ${fullseye_PYTHON_EXECUTABLE}\n"
    "Windows: py -3.11 -m pip install --upgrade fullseye\n"
    "Linux:   sudo apt-get install python3.11-dev\n"
    "macOS:   brew install python@3.11")
endif()

execute_process(
  COMMAND "${fullseye_PYTHON_EXECUTABLE}" -m pybind11 --cmakedir
  RESULT_VARIABLE _fullseye_pybind_status
  OUTPUT_VARIABLE pybind11_DIR
  ERROR_VARIABLE _fullseye_pybind_error
  OUTPUT_STRIP_TRAILING_WHITESPACE)
string(REGEX REPLACE "^\"(.*)\"$" "\\1" pybind11_DIR "${pybind11_DIR}")
if(NOT _fullseye_pybind_status EQUAL 0 OR "${pybind11_DIR}" STREQUAL "")
  message(FATAL_ERROR
    "Fullseye needs its installed pybind11 headers, but they are unavailable: ${_fullseye_pybind_error}\n"
    "Windows: py -3.11 -m pip install --force-reinstall fullseye\n"
    "Linux:   python3 -m pip install --force-reinstall fullseye\n"
    "macOS:   python3 -m pip install --force-reinstall fullseye")
endif()
find_package(pybind11 2.13.6 CONFIG QUIET
  PATHS "${pybind11_DIR}"
  NO_DEFAULT_PATH)
if(NOT pybind11_FOUND)
  message(FATAL_ERROR
    "Fullseye found pybind11's directory but not compatible pybind11 2.13.6 headers.\n"
    "Windows: py -3.11 -m pip install --force-reinstall fullseye\n"
    "Linux:   python3 -m pip install --force-reinstall fullseye\n"
    "macOS:   python3 -m pip install --force-reinstall fullseye")
endif()

add_library(fullseye_source_bridge SHARED "${fullseye_SDK_SOURCE_FILE}")
add_library(fullseye::fullseye ALIAS fullseye_source_bridge)
target_compile_features(fullseye_source_bridge PUBLIC cxx_std_20)
target_compile_definitions(fullseye_source_bridge PRIVATE
  FULLSEYE_BUILD
  PYBIND11_SIMPLE_GIL_MANAGEMENT)
if(MSVC)
  # The bridge source and the public headers contain UTF-8 Japanese text. Without /utf-8,
  # MSVC reads them in the system code page (932 on Japanese Windows) and a string literal
  # breaks (C2001). PUBLIC so a consumer that includes the headers reads them the same way.
  # bridge のソースと公開ヘッダは UTF-8 の日本語を含む。/utf-8 が無いと MSVC は既定の
  # コードページ(日本語 Windows は 932)で読み、文字列リテラルが壊れる(C2001)。
  target_compile_options(fullseye_source_bridge PUBLIC /utf-8)
  target_compile_definitions(fullseye_source_bridge PRIVATE NOMINMAX)
endif()
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
  # venv's Scripts directory normally has no DLL; FindPython resolves the
  # selected interpreter's base runtime directory.  Search only that declared
  # development-runtime location, never PATH. / venv の Scripts には通常 DLL
  # が無いので、FindPython が解決した base runtime だけを探し、PATH は見ない。
  if(NOT EXISTS "${_fullseye_python_runtime}")
    foreach(_fullseye_python_runtime_dir IN LISTS Python_RUNTIME_LIBRARY_DIRS)
      set(_fullseye_candidate_runtime
          "${_fullseye_python_runtime_dir}/python${Python_VERSION_MAJOR}${Python_VERSION_MINOR}.dll")
      if(EXISTS "${_fullseye_candidate_runtime}")
        set(_fullseye_python_runtime "${_fullseye_candidate_runtime}")
        break()
      endif()
    endforeach()
  endif()
  if(NOT EXISTS "${_fullseye_python_runtime}")
    message(FATAL_ERROR
      "Fullseye could not locate Python's runtime DLL for ${fullseye_PYTHON_EXECUTABLE}")
  endif()
  add_custom_command(TARGET fullseye_source_bridge POST_BUILD
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different
            "${_fullseye_python_runtime}" "$<TARGET_FILE_DIR:fullseye_source_bridge>")
endif()
set_target_properties(fullseye_source_bridge PROPERTIES
  OUTPUT_NAME fullseye
  CXX_VISIBILITY_PRESET hidden
  VISIBILITY_INLINES_HIDDEN YES)

# Install a manifest beside an executable at generation/build time.  It records
# paths as data, so ``python -m fullseye.sdk relink <directory>`` can repair a
# moved venv without changing the compiled bridge. / パスを DLL に焼かず manifest
# に記録するため、venv 移動後も relink だけで直せる。
function(_fullseye_json_escape value out)
  set(_fullseye_json "${value}")
  string(REPLACE "\\" "\\\\" _fullseye_json "${_fullseye_json}")
  string(REPLACE "\"" "\\\"" _fullseye_json "${_fullseye_json}")
  string(REPLACE "\n" "\\n" _fullseye_json "${_fullseye_json}")
  set(${out} "${_fullseye_json}" PARENT_SCOPE)
endfunction()

function(fullseye_deploy_runtime target)
  if(NOT TARGET "${target}")
    message(FATAL_ERROR "fullseye_deploy_runtime expects an existing executable target, got: ${target}")
  endif()
  get_property(_fullseye_target_type TARGET "${target}" PROPERTY TYPE)
  if(NOT _fullseye_target_type STREQUAL "EXECUTABLE")
    message(FATAL_ERROR "fullseye_deploy_runtime accepts executable targets only, got ${target}")
  endif()
  _fullseye_json_escape("${fullseye_PYTHON_EXECUTABLE}" _fullseye_manifest_python)
  _fullseye_json_escape("${fullseye_PYTHON_HOME}" _fullseye_manifest_home)
  _fullseye_json_escape("${fullseye_PYTHON_RUNTIME_ROOT}" _fullseye_manifest_root)
  string(TIMESTAMP _fullseye_manifest_time "%Y-%m-%dT%H:%M:%SZ" UTC)
  set(_fullseye_manifest "{\n  \"python_executable\": \"${_fullseye_manifest_python}\",\n  \"python_home\": \"${_fullseye_manifest_home}\",\n  \"runtime_root\": \"${_fullseye_manifest_root}\",\n  \"sdk_abi_version\": \"${fullseye_SDK_ABI_VERSION}\",\n  \"created_at\": \"${_fullseye_manifest_time}\"\n}\n")
  set(_fullseye_manifest_source "${CMAKE_CURRENT_BINARY_DIR}/fullseye-runtime-${target}.json")
  file(GENERATE OUTPUT "${_fullseye_manifest_source}" CONTENT "${_fullseye_manifest}")
  add_custom_command(TARGET "${target}" POST_BUILD
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different "${_fullseye_manifest_source}"
            "$<TARGET_FILE_DIR:${target}>/fullseye_runtime.json"
    VERBATIM)
endfunction()
