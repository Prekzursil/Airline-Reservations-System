// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"
#include "../src/ReservationSystemHelpers.h"

#include <sstream>
#include <vector>

namespace rsh = reservation_system_helpers;

namespace {
void expect_book_seat_prerequisites_result(
    const std::vector<Airplane>& airplanes,
    const std::vector<Customer>& customers,
    const std::string& expected_output
) {
    std::ostringstream output;

    const bool ready = rsh::hasBookSeatPrerequisites(output, airplanes, customers);

    EXPECT_FALSE(ready);
    EXPECT_EQ(output.str(), expected_output);
}
} // namespace

TEST(ReservationSystemHelpersTest, ReadNonEmptyLineRetriesOnceAfterEmptyInput) {
    std::istringstream input("\nRecovered Name\n");
    std::ostringstream output;

    const std::string value = rsh::readNonEmptyLine(input, output, "Enter customer name: ");

    EXPECT_EQ(value, "Recovered Name");
    EXPECT_EQ(
        output.str(),
        "Enter customer name: Input cannot be empty. Please try again: ");
}

TEST(ReservationSystemHelpersTest, ReadNonEmptyLineReturnsImmediateNonEmptyInput) {
    std::istringstream input("Direct Value\n");
    std::ostringstream output;

    const std::string value = rsh::readNonEmptyLine(input, output, "Enter customer name: ");

    EXPECT_EQ(value, "Direct Value");
    EXPECT_EQ(output.str(), "Enter customer name: ");
}

TEST(ReservationSystemHelpersTest, ReadNonEmptyLineReturnsSecondAttemptEvenIfStillEmpty) {
    std::istringstream input("\n\n");
    std::ostringstream output;

    const std::string value = rsh::readNonEmptyLine(input, output, "Enter customer name: ");

    EXPECT_TRUE(value.empty());
    EXPECT_EQ(
        output.str(),
        "Enter customer name: Input cannot be empty. Please try again: ");
}

TEST(ReservationSystemHelpersTest, ReadNonEmptyLineThrowsWhenInputIsAlreadyExhausted) {
    std::istringstream input;
    std::ostringstream output;

    EXPECT_THROW(
        static_cast<void>(rsh::readNonEmptyLine(input, output, "Enter customer name: ")),
        rsh::InputExhaustedError);
    EXPECT_EQ(output.str(), "Enter customer name: ");
}

TEST(ReservationSystemHelpersTest, ReadNonEmptyLineThrowsWhenRetryHitsEof) {
    std::istringstream input("\n");
    std::ostringstream output;

    EXPECT_THROW(
        static_cast<void>(rsh::readNonEmptyLine(input, output, "Enter customer name: ")),
        rsh::InputExhaustedError);
    EXPECT_EQ(
        output.str(),
        "Enter customer name: Input cannot be empty. Please try again: ");
}

TEST(ReservationSystemHelpersTest, FormatMoneyAmountPadsSingleDigitCents) {
    EXPECT_EQ(rsh::formatMoneyAmount(12.04), "12.04");
}

TEST(ReservationSystemHelpersTest, FormatMoneyAmountRoundsNegativeValues) {
    EXPECT_EQ(rsh::formatMoneyAmount(-12.04), "-12.04");
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

TEST(ReservationSystemHelpersTest, PrintSeatSuggestionsReturnsSilentlyWhenThereAreNoSuggestions) {
    std::ostringstream output;

    rsh::printSeatSuggestions(output, {});

    EXPECT_TRUE(output.str().empty());
}

TEST(ReservationSystemHelpersTest, HasBookSeatPrerequisitesRejectsEmptyAirplaneList) {
    const std::vector<Airplane> airplanes;
    const std::vector<Customer> customers = {Customer{"Ready Customer", 34, "CUST001", 120.0}};

    expect_book_seat_prerequisites_result(airplanes, customers, "No flights available to book.\n");
}

TEST(ReservationSystemHelpersTest, HasBookSeatPrerequisitesRejectsEmptyCustomerList) {
    const std::vector<Airplane> airplanes = {Airplane{"FL101", 2, 2}};
    const std::vector<Customer> customers;

    expect_book_seat_prerequisites_result(
        airplanes,
        customers,
        "No customers in the system. Please add a customer first.\n");
}
