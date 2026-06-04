// ═══════════════════════════════════════════════════════════════
//  Python Bindings Template for Room
//  Place as: integration/output/mesh/<room>/bindings.cpp
// ═══════════════════════════════════════════════════════════════

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <aizquad/mesh_core.hpp>

// Include room-specific headers
// #include "core/process.hpp"
// #include "validation/validate.hpp"

namespace py = pybind11;
using namespace aizquad::mesh;

PYBIND11_MODULE(room_2_py, m) {
    m.doc() = "Python bindings for room-2";
    
    // Expose Surface wrapper
    py::class_<Surface<IRoom>>(m, "Surface")
        .def("is_valid", &Surface<IRoom>::is_valid)
        ;
    
    // Expose room-specific classes
    // py::class_<ProcessEngine>(m, "ProcessEngine")
    //     .def(py::init<>())
    //     .def("process", &ProcessEngine::process)
    //     ;
    
    // Expose functions
    // m.def("validate", &validate, "Validate input data");
    
    // Module constants
    m.attr("__version__") = "1.0.0";
    m.attr("ROOM_NAME") = "room-2";
}
# ═══════════════════════════════════════════════════════════════
#  BUILD C++ COMPONENTS
# ═══════════════════════════════════════════════════════════════

# Standard build
make cpp-build

# Debug build with sanitizers
make cpp-build BUILD_TYPE=Debug ENABLE_SANITIZERS=ON

# Release with LTO
make cpp-build BUILD_TYPE=Release ENABLE_LTO=ON

# Build with tests
make cpp-build BUILD_TESTS=ON
make cpp-test

# Build with Python bindings
make cpp-build ENABLE_PYTHON_BINDINGS=ON

# ═══════════════════════════════════════════════════════════════
#  MANUAL CMAKE
# ═══════════════════════════════════════════════════════════════

mkdir -p build/cpp
cd build/cpp

# Configure
cmake ../.. \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTS=ON \
    -DENABLE_PYTHON_BINDINGS=ON \
    -DENABLE_LTO=ON

# Build
cmake --build . --config Release -j$(nproc)

# Test
ctest --output-on-failure

# Install
sudo cmake --install .

# ═══════════════════════════════════════════════════════════════
#  USE FROM PYTHON
# ═══════════════════════════════════════════════════════════════

import room_2_py

surface = room_2_py.Surface()
if surface.is_valid():
    result = surface.process(data)
