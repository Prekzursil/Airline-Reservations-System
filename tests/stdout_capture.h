#pragma once
// cppcheck-suppress-file missingIncludeSystem
#include <iostream>
#include <sstream>
#include <string>
#include <utility>

namespace test_support {

// Runs `action` with std::cout redirected into a local buffer and returns the
// captured text. Centralizes the redirect/restore boilerplate that the
// console-output tests would otherwise repeat for every assertion.
template <typename Action>
std::string captureStdout(Action&& action) {
    std::ostringstream captured;
    std::streambuf* const original = std::cout.rdbuf(captured.rdbuf());
    std::forward<Action>(action)();
    std::cout.rdbuf(original);
    return captured.str();
}

}  // namespace test_support
