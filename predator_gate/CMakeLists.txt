cmake_minimum_required(VERSION 3.18)
project(PredatorGate VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenSSL REQUIRED)
find_package(Threads REQUIRED)

add_library(predator_gate_shared SHARED
    src/ram_wiper.cpp
    src/token.cpp
    src/fuel_flow.cpp
    src/stats.cpp
    src/logger.cpp
    src/predator_gate.cpp
    src/predator_bridge_api.cpp
)

set_target_properties(predator_gate_shared PROPERTIES
    OUTPUT_NAME predator_gate
    C_VISIBILITY_PRESET hidden
    CXX_VISIBILITY_PRESET hidden
)

target_include_directories(predator_gate_shared PUBLIC include)
target_link_libraries(predator_gate_shared PUBLIC OpenSSL::Crypto PRIVATE Threads::Threads)

add_custom_command(TARGET predator_gate_shared POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_SOURCE_DIR}/python
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:predator_gate_shared>
            ${CMAKE_SOURCE_DIR}/python/libpredator_gate.so
)
