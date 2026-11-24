#include "mcnative/version.hpp"

#include <cassert>

int main() {
    assert(mcnative::project_name() == "Minecraft C++ Native");
    assert(mcnative::target_game_version() == "26.3");
    assert(mcnative::cpp_standard() == "C++20");
    return 0;
}
