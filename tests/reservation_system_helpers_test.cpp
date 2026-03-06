// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"
#include "../src/ReservationSystemHelpers.h"

#include <sstream>
#include <vector>

namespace rsh = reservation_system_helpers;

TEST(ReservationSystemHelpersTest, ReadNonEmptyLineRetriesOnceAfterEmptyInput) {
    std::istringstream input("\nRecovered Name\n");
    std::ostringstream output;

    const std::string value = rsh::readNonEmptyLine(input, output, "Enter customer name: ");

    EXPECT_EQ(value, "Recovered Name");
    EXPECT_EQ(
        output.str(),
        "Enter customer name: Input cannot be empty. Please try again: ");
}

TEST(ReservationSystemHelpersTest, FormatMoneyAmountPadsSingleDigitCents) {
    EXPECT_EQ(rsh::formatMoneyAmount(12.04), "12.04");
}

TEST(ReservationSystemHelpersTest, PrintSeatSuggestionsSkipsNullPointersAndPrintsValidSeats) {
    Seat suggestedSeat("4A", SeatClass::ECONOMY, 50.0);
    const std::vector<const Seat*> suggestions = {nullptr, &suggestedSeat};
    std::ostringstream output;

    rsh::printSeatSuggestions(output, suggestions);

    EXPECT_EQ(
        output.str(),
        "Perhaps one of these seats instead?\n"
        "- 4A (Economy) costs $50\n");
}
