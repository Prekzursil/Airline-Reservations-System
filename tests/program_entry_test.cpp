// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"

#include <sstream>

#define main airline_cli_entry_main
#include "../src/main.cpp"
#undef main

namespace {
std::pair<int, std::string> run_cli_main(const std::string& input_text) {
    std::istringstream input(input_text);
    std::ostringstream output;

    std::streambuf* original_in = std::cin.rdbuf(input.rdbuf());
    std::streambuf* original_out = std::cout.rdbuf(output.rdbuf());

    const int exit_code = airline_cli_entry_main();

    std::cin.rdbuf(original_in);
    std::cout.rdbuf(original_out);

    return {exit_code, output.str()};
}
} // namespace

TEST(ProgramEntryTest, MainExitsCleanlyWhenExitIsSelected) {
    const auto [exit_code, output] = run_cli_main("0\n");

    EXPECT_EQ(exit_code, 0);
    EXPECT_NE(output.find("Welcome to the Airline Reservation System!"), std::string::npos);
    EXPECT_NE(output.find("Exiting system. Goodbye!"), std::string::npos);
    EXPECT_NE(output.find("Thank you for using the Airline Reservation System."), std::string::npos);
}

TEST(ProgramEntryTest, MainExitsCleanlyWhenMenuInputEndsAtEof) {
    const auto [exit_code, output] = run_cli_main("");

    EXPECT_EQ(exit_code, 0);
    EXPECT_NE(output.find("Input stream exhausted. Exiting system."), std::string::npos);
    EXPECT_NE(output.find("Thank you for using the Airline Reservation System."), std::string::npos);
}

TEST(ProgramEntryTest, MainExitsCleanlyWhenInputEndsMidOperation) {
    const auto [exit_code, output] = run_cli_main("1\nm\n");

    EXPECT_EQ(exit_code, 0);
    EXPECT_NE(output.find("--- Add New Customer ---"), std::string::npos);
    EXPECT_NE(output.find("Input stream exhausted. Exiting system."), std::string::npos);
    EXPECT_NE(output.find("Thank you for using the Airline Reservation System."), std::string::npos);
}
