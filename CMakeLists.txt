cmake_minimum_required(VERSION 3.0)
project(torchscatter)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED)
set(TORCHSCATTER_VERSION 2.1.2)

option(WITH_CUDA "Enable CUDA support" OFF)
option(WITH_PYTHON "Link to Python when building" ON)

if(WITH_CUDA)
  enable_language(CUDA)
  add_definitions(-D__CUDA_NO_HALF_OPERATORS__)
  add_definitions(-DWITH_CUDA)
  set(CMAKE_CUDA_FLAGS "${CMAKE_CUDA_FLAGS} --expt-relaxed-constexpr")
endif()

if (WITH_PYTHON)
  add_definitions(-DWITH_PYTHON)
  find_package(Python3 COMPONENTS Development)
endif()
find_package(Torch REQUIRED)

# Function to create a library for each operation
function(add_scatter_library name sources)
  add_library(${name} SHARED ${sources})
  target_link_libraries(${name} PRIVATE ${TORCH_LIBRARIES})
  if (WITH_PYTHON)
    target_link_libraries(${name} PRIVATE Python3::Python)
  endif()
  target_include_directories(${name} PRIVATE csrc)
  
  # Set output name to match Python expectations (no prefix, no suffix)
  set_target_properties(${name} PROPERTIES PREFIX "")
  if(NOT WIN32)
    set_target_properties(${name} PROPERTIES SUFFIX ".so")
  endif()
  
  # Install to the Python package directory (CMAKE_INSTALL_PREFIX is set to torch_scatter)
  install(TARGETS ${name} LIBRARY DESTINATION .)
endfunction()

# Build version library
add_scatter_library(_version_cpu csrc/version.cpp)
if(WITH_CUDA)
  add_scatter_library(_version_cuda csrc/version.cpp)
endif()

# Build scatter libraries
add_scatter_library(_scatter_cpu "csrc/scatter.cpp;csrc/cpu/scatter_cpu.cpp")
if(WITH_CUDA)
  add_scatter_library(_scatter_cuda "csrc/scatter.cpp;csrc/cpu/scatter_cpu.cpp;csrc/cuda/scatter_cuda.cu")
endif()

# Build segment_csr libraries
add_scatter_library(_segment_csr_cpu "csrc/segment_csr.cpp;csrc/cpu/segment_csr_cpu.cpp")
if(WITH_CUDA)
  add_scatter_library(_segment_csr_cuda "csrc/segment_csr.cpp;csrc/cpu/segment_csr_cpu.cpp;csrc/cuda/segment_csr_cuda.cu")
endif()

# Build segment_coo libraries
add_scatter_library(_segment_coo_cpu "csrc/segment_coo.cpp;csrc/cpu/segment_coo_cpu.cpp")
if(WITH_CUDA)
  add_scatter_library(_segment_coo_cuda "csrc/segment_coo.cpp;csrc/cpu/segment_coo_cpu.cpp;csrc/cuda/segment_coo_cuda.cu")
endif()

# Install CMake configuration files for downstream usage
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

file(GLOB HEADERS csrc/*.h)
set(TORCHSCATTER_CMAKECONFIG_INSTALL_DIR "share/cmake/TorchScatter" CACHE STRING "install path for TorchScatterConfig.cmake")

configure_package_config_file(cmake/TorchScatterConfig.cmake.in
  "${CMAKE_CURRENT_BINARY_DIR}/TorchScatterConfig.cmake"
  INSTALL_DESTINATION ${TORCHSCATTER_CMAKECONFIG_INSTALL_DIR})

write_basic_package_version_file(${CMAKE_CURRENT_BINARY_DIR}/TorchScatterConfigVersion.cmake
  VERSION ${TORCHSCATTER_VERSION}
  COMPATIBILITY AnyNewerVersion)

install(FILES ${CMAKE_CURRENT_BINARY_DIR}/TorchScatterConfig.cmake
  ${CMAKE_CURRENT_BINARY_DIR}/TorchScatterConfigVersion.cmake
  DESTINATION ${TORCHSCATTER_CMAKECONFIG_INSTALL_DIR})

# Create a legacy library target for backward compatibility
add_library(torchscatter INTERFACE)
set_target_properties(torchscatter PROPERTIES EXPORT_NAME TorchScatter)
target_include_directories(torchscatter INTERFACE
  "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/csrc>"
  $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)

install(TARGETS torchscatter
  EXPORT TorchScatterTargets)

install(EXPORT TorchScatterTargets
  NAMESPACE TorchScatter::
  DESTINATION ${TORCHSCATTER_CMAKECONFIG_INSTALL_DIR})

install(FILES ${HEADERS} DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/${PROJECT_NAME})
install(FILES
  csrc/cpu/scatter_cpu.h
  csrc/cpu/segment_coo_cpu.h
  csrc/cpu/segment_csr_cpu.h
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/${PROJECT_NAME}/cpu)
if(WITH_CUDA)
  install(FILES
    csrc/cuda/scatter_cuda.h
    csrc/cuda/segment_coo_cuda.h
    csrc/cuda/segment_csr_cuda.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/${PROJECT_NAME}/cuda)
endif()

if(WITH_CUDA)
  set_property(TARGET torch_cuda PROPERTY INTERFACE_COMPILE_OPTIONS "")
  set_property(TARGET torch_cpu PROPERTY INTERFACE_COMPILE_OPTIONS "")
endif()
