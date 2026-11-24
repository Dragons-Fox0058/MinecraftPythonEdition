#pragma once

#include <string_view>

namespace mcnative {

[[nodiscard]] constexpr std::string_view project_name() noexcept {
    return "Minecraft C++ Native";
}

[[nodiscard]] constexpr std::string_view target_game_version() noexcept {
    return "26.3";
}

[[nodiscard]] constexpr std::string_view cpp_standard() noexcept {
    return "C++20";
}

} // namespace mcnative
