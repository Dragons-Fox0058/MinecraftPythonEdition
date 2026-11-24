cmake_minimum_required(VERSION 3.24)

project(MinecraftCppNative
    VERSION 0.2.0
    DESCRIPTION "Native Java-to-C++ compatibility toolchain targeting Minecraft 26.3"
    LANGUAGES CXX
)

option(MCNATIVE_BUILD_TESTS "Build unit and smoke tests" ON)

add_library(mcnative_core
    src/version.cpp
    src/class_file.cpp
)
target_include_directories(mcnative_core PUBLIC include)
target_compile_features(mcnative_core PUBLIC cxx_std_20)

if(MSVC)
    target_compile_options(mcnative_core PRIVATE /W4 /permissive- /EHsc)
else()
    target_compile_options(mcnative_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(mc-native-tool
    src/main.cpp
)
target_link_libraries(mc-native-tool PRIVATE mcnative_core)

if(MCNATIVE_BUILD_TESTS)
    enable_testing()

    add_executable(mcnative_smoke_test tests/smoke_test.cpp)
    target_link_libraries(mcnative_smoke_test PRIVATE mcnative_core)
    add_test(NAME mcnative_smoke_test COMMAND mcnative_smoke_test)

    add_executable(mcnative_class_file_test tests/class_file_test.cpp)
    target_link_libraries(mcnative_class_file_test PRIVATE mcnative_core)
    add_test(NAME mcnative_class_file_test COMMAND mcnative_class_file_test)
endif()
