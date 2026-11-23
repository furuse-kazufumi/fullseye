cmake_minimum_required(VERSION 3.21)
project(Fullseye VERSION 0.1.0 LANGUAGES C CXX)

set(FULLSEYE_ABI_MAJOR 0)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

option(FULLSEYE_BUILD_NATIVE "Build the optional pybind11 C ABI bridge" ON)
option(FULLSEYE_BUILD_TESTS "Build native C/C++ examples and CTest gates" ON)
option(FULLSEYE_ENABLE_SANITIZERS "Enable AddressSanitizer and UndefinedBehaviorSanitizer" OFF)

if(FULLSEYE_BUILD_NATIVE)
  find_package(Python 3.11 EXACT COMPONENTS Interpreter Development.Embed REQUIRED)
  find_package(pybind11 2.13.6 CONFIG REQUIRED)

  add_library(fullseye_c_api SHARED native/fullseye_c_api.cpp)
  add_library(Fullseye::C ALIAS fullseye_c_api)
  target_compile_features(fullseye_c_api PRIVATE cxx_std_17)
  # Use CPython's PyGILState API for foreign C threads.  pybind11's custom TLS
  # thread-state cache is unnecessary here and is not ABI-safe across every
  # Windows CRT/toolchain combination used by SDK consumers.
  # 外部 C スレッドでは CPython 標準の PyGILState API を使う。
  target_compile_definitions(fullseye_c_api PRIVATE FULLSEYE_BUILD PYBIND11_SIMPLE_GIL_MANAGEMENT)
  target_include_directories(fullseye_c_api
    PUBLIC
      $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
      $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/fullseye>)
  target_link_libraries(fullseye_c_api PRIVATE pybind11::embed)
  if(MINGW)
    # The SDK DLL must not depend on a compiler installation being on PATH.
    # SDK DLL はコンパイラー導入先の PATH に依存させない。
    target_link_options(fullseye_c_api PRIVATE -static-libgcc -static-libstdc++)
    get_filename_component(_fullseye_mingw_bin "${CMAKE_CXX_COMPILER}" DIRECTORY)
    get_filename_component(_fullseye_mingw_root "${_fullseye_mingw_bin}" DIRECTORY)
    file(GLOB _fullseye_winpthread "${_fullseye_mingw_root}/*/lib/libwinpthread.a")
    if(_fullseye_winpthread)
      target_link_libraries(fullseye_c_api PRIVATE "${_fullseye_winpthread}")
    endif()
  endif()
  set_target_properties(fullseye_c_api PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN YES
    EXPORT_NAME C)
  if(WIN32)
    set_target_properties(fullseye_c_api PROPERTIES OUTPUT_NAME "fullseye-${FULLSEYE_ABI_MAJOR}")
  else()
    set_target_properties(fullseye_c_api PROPERTIES OUTPUT_NAME fullseye
                                                   VERSION ${PROJECT_VERSION}
                                                   SOVERSION ${FULLSEYE_ABI_MAJOR})
  endif()

  if(FULLSEYE_ENABLE_SANITIZERS AND CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(fullseye_c_api PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
    target_link_options(fullseye_c_api PRIVATE -fsanitize=address,undefined)
  endif()

  add_library(fullseye_cxx INTERFACE)
  add_library(Fullseye::CXX ALIAS fullseye_cxx)
  target_compile_features(fullseye_cxx INTERFACE cxx_std_17)
  target_link_libraries(fullseye_cxx INTERFACE Fullseye::C)
  target_include_directories(fullseye_cxx
    INTERFACE
      $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
      $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}/fullseye>)
  set_target_properties(fullseye_cxx PROPERTIES EXPORT_NAME CXX)

  install(TARGETS fullseye_c_api fullseye_cxx EXPORT FullseyeTargets
          RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
          LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
          ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
  install(FILES fullseye.h fullseye.hpp fullseye_abi.h
          DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/fullseye)
  install(EXPORT FullseyeTargets NAMESPACE Fullseye::
          DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Fullseye)

  configure_package_config_file(
    cmake/FullseyeConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/FullseyeConfig.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Fullseye)
  write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/FullseyeConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion)
  install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/FullseyeConfig.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/FullseyeConfigVersion.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/Fullseye)

  if(FULLSEYE_BUILD_TESTS)
    enable_testing()
    find_package(Threads REQUIRED)
    add_executable(fullseye_c_example examples/c_api.c)
    set_property(TARGET fullseye_c_example PROPERTY C_STANDARD 11)
    target_link_libraries(fullseye_c_example PRIVATE Fullseye::C)
    add_executable(fullseye_cpp_example examples/cpp_api.cpp)
    target_link_libraries(fullseye_cpp_example PRIVATE Fullseye::CXX)
    add_executable(fullseye_c_threads examples/c_threads.c)
    set_property(TARGET fullseye_c_threads PROPERTY C_STANDARD 11)
    target_link_libraries(fullseye_c_threads PRIVATE Fullseye::C Threads::Threads)
    add_executable(fullseye_c_handle_safety examples/c_handle_safety.c)
    set_property(TARGET fullseye_c_handle_safety PROPERTY C_STANDARD 11)
    target_link_libraries(fullseye_c_handle_safety PRIVATE Fullseye::C Threads::Threads)
    add_executable(fullseye_c_abi_0_1_consumer tests/c_abi_0_1_consumer.c)
    set_property(TARGET fullseye_c_abi_0_1_consumer PROPERTY C_STANDARD 11)
    target_link_libraries(fullseye_c_abi_0_1_consumer PRIVATE Fullseye::C)
    add_executable(fullseye_c_runtime_configuration examples/c_runtime_configuration.c)
    set_property(TARGET fullseye_c_runtime_configuration PROPERTY C_STANDARD 11)
    target_link_libraries(fullseye_c_runtime_configuration PRIVATE Fullseye::C)
    add_test(NAME fullseye_c_lifecycle
             COMMAND fullseye_c_example ${CMAKE_CURRENT_SOURCE_DIR})
    add_test(NAME fullseye_cpp_lifecycle
             COMMAND fullseye_cpp_example ${CMAKE_CURRENT_SOURCE_DIR})
    add_test(NAME fullseye_c_thread_errors
             COMMAND fullseye_c_threads ${CMAKE_CURRENT_SOURCE_DIR})
    add_test(NAME fullseye_c_handle_safety
             COMMAND fullseye_c_handle_safety ${CMAKE_CURRENT_SOURCE_DIR})
    add_test(NAME fullseye_c_abi_0_1_consumer
             COMMAND fullseye_c_abi_0_1_consumer ${CMAKE_CURRENT_SOURCE_DIR})
    add_test(NAME fullseye_c_runtime_configuration
             COMMAND fullseye_c_runtime_configuration ${CMAKE_CURRENT_SOURCE_DIR})
  endif()
endif()
