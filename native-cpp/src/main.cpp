#include "mcnative/version.hpp"

#include <iostream>
#include <string_view>

int main(int argc, char** argv) {
    if (argc > 1 && std::string_view{argv[1]} == "--version") {
        std::cout << mcnative::project_name() << " — target Minecraft Java "
                  << mcnative::target_game_version() << " (" 
                  << mcnative::cpp_standard() << ")\n";
        return 0;
    }

    std::cout << mcnative::project_name() << '\n'
              << "Target: Minecraft Java Edition "
              << mcnative::target_game_version() << '\n'
              << "Status: scaffold only; bytecode analysis/code generation is not implemented yet.\n"
              << "Run with --version to print version metadata.\n";
    return 0;
}
