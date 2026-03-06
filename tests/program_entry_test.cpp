// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"

#include <sstream>

#define main airline_cli_entry_main
#include "../src/main.cpp"
#undef main

TEST(ProgramEntryTest, MainExitsCleanlyWhenExitIsSelected) {
    std::istringstream input("0\n");
    std::ostringstream output;

    std::streambuf* original_in = std::cin.rdbuf(input.rdbuf());
    std::streambuf* original_out = std::cout.rdbuf(output.rdbuf());

    const int exit_code = airline_cli_entry_main();

    std::cin.rdbuf(original_in);
    std::cout.rdbuf(original_out);

    EXPECT_EQ(exit_code, 0);
    EXPECT_NE(output.str().find("Welcome to the Airline Reservation System!"), std::string::npos);
    EXPECT_NE(output.str().find("Exiting system. Goodbye!"), std::string::npos);
    EXPECT_NE(output.str().find("Thank you for using the Airline Reservation System."), std::string::npos);
}
