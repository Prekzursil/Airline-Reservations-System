// cppcheck-suppress-file missingIncludeSystem
#include "gtest/gtest.h"
#include "../src/ReservationSystemHelpers.h"

#include <algorithm>
#include <sstream>
#include <string_view>
#include <ranges>
#include <vector>

namespace rsh = reservation_system_helpers;

namespace {
bool all_seen(const std::vector<bool>& seen) {
    return std::ranges::all_of(seen, [](bool value) { return value; });
}

void mark_seen(
    const std::vector<std::string_view>& prefixes,
    std::string_view name,
    std::vector<bool>& seen
) {
    for (std::size_t index = 0; index < prefixes.size(); ++index) {
        if (name.starts_with(prefixes[index])) {
            seen[index] = true;
        }
    }
}

void expect_book_seat_prerequisites_result(
    const std::vector<Airplane>& airplanes,
    const std::vector<Customer>& customers,
    std::string_view expected_output
) {
    std::ostringstream output;

    const bool ready = rsh::hasBookSeatPrerequisites(output, airplanes, customers.size());

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

TEST(ReservationSystemHelpersTest, InputExhaustedErrorExposesStableMessage) {
    const rsh::InputExhaustedError error;

    EXPECT_STREQ(error.what(), "Input stream exhausted");
}

TEST(ReservationSystemHelpersTest, FormatMoneyAmountPadsSingleDigitCents) {
    EXPECT_EQ(rsh::formatMoneyAmount(12.04), "12.04");
}

TEST(ReservationSystemHelpersTest, FormatMoneyAmountRoundsNegativeValues) {
    EXPECT_EQ(rsh::formatMoneyAmount(-12.04), "-12.04");
}

TEST(ReservationSystemHelpersTest, IsAffirmativeAcceptsLowerAndUpperCaseYOnly) {
    EXPECT_TRUE(rsh::isAffirmative('y'));
    EXPECT_TRUE(rsh::isAffirmative('Y'));
    EXPECT_FALSE(rsh::isAffirmative('n'));
    EXPECT_FALSE(rsh::isAffirmative('N'));
}

TEST(ReservationSystemHelpersTest, GenerateAutoCustomerDataIsDeterministicAndInExpectedRange) {
    const rsh::AutoCustomerData first = rsh::generateAutoCustomerData("CUST0007");
    const rsh::AutoCustomerData second = rsh::generateAutoCustomerData("CUST0007");

    EXPECT_EQ(first.name, second.name);
    EXPECT_EQ(first.age, second.age);
    EXPECT_DOUBLE_EQ(first.money, second.money);
    EXPECT_TRUE(first.name.ends_with("_CUST0007"));
    EXPECT_GE(first.age, 18);
    EXPECT_LE(first.age, 80);
    EXPECT_GE(first.money, 100.0);
    EXPECT_LE(first.money, 2000.0);
}

TEST(ReservationSystemHelpersTest, GenerateApiAutoCustomerDataIsDeterministicAndInExpectedRange) {
    const rsh::AutoCustomerData first = rsh::generateApiAutoCustomerData("CUST0008");
    const rsh::AutoCustomerData second = rsh::generateApiAutoCustomerData("CUST0008");

    EXPECT_EQ(first.name, second.name);
    EXPECT_EQ(first.age, second.age);
    EXPECT_DOUBLE_EQ(first.money, second.money);
    EXPECT_TRUE(first.name.ends_with("_CUST0008"));
    EXPECT_GE(first.age, 18);
    EXPECT_LE(first.age, 80);
    EXPECT_GE(first.money, 100.0);
    EXPECT_LE(first.money, 2000.0);
}

TEST(ReservationSystemHelpersTest, GenerateAutoCustomerDataCoversAllNameVariants) {
    const std::vector<std::string_view> console_prefixes = {
        "AutoPat_",
        "RoboUser_",
        "GenClient_",
        "SysPerson_",
        "BotPassenger_",
    };
    const std::vector<std::string_view> api_prefixes = {
        "ApiPat_",
        "WebServiceUser_",
        "JsonGenClient_",
        "SystemPerson_",
        "BackendBot_",
    };
    std::vector<bool> console_seen(console_prefixes.size(), false);
    std::vector<bool> api_seen(api_prefixes.size(), false);

    for (int counter = 1; counter <= 200 && (!all_seen(console_seen) || !all_seen(api_seen)); ++counter) {
        const std::string customer_id = rsh::formatCustomerId(counter);
        mark_seen(console_prefixes, rsh::generateAutoCustomerData(customer_id).name, console_seen);
        mark_seen(api_prefixes, rsh::generateApiAutoCustomerData(customer_id).name, api_seen);
    }

    EXPECT_TRUE(all_seen(console_seen));
    EXPECT_TRUE(all_seen(api_seen));
}

TEST(ReservationSystemHelpersTest, FormatCustomerIdPadsValuesToAtLeastFourDigits) {
    EXPECT_EQ(rsh::formatCustomerId(7), "CUST0007");
    EXPECT_EQ(rsh::formatCustomerId(1234), "CUST1234");
    EXPECT_EQ(rsh::formatCustomerId(12345), "CUST12345");
}

TEST(ReservationSystemHelpersTest, PrintAvailableFlightsListsIndexedFlightNumbers) {
    const std::vector<Airplane> airplanes = {
        Airplane{"FL101", 2, 2},
        Airplane{"FL202", 3, 2},
    };
    std::ostringstream output;

    rsh::printAvailableFlights(output, airplanes);

    EXPECT_EQ(
        output.str(),
        "\nAvailable Flights:\n"
        "1. Flight FL101\n"
        "2. Flight FL202\n");
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

TEST(ReservationSystemHelpersTest, HasBookSeatPrerequisitesReturnsTrueWhenSystemIsReady) {
    const std::vector<Airplane> airplanes = {Airplane{"FL101", 2, 2}};
    std::ostringstream output;

    const auto ready = rsh::hasBookSeatPrerequisites(output, airplanes, 1U);

    EXPECT_TRUE(ready);
    EXPECT_TRUE(output.str().empty());
}

TEST(ReservationSystemHelpersTest, TryPrepareSeatForBookingRejectsMissingSeat) {
    Airplane airplane("FL101", 2, 2);
    Customer customer("Seat Hunter", 29, "CUST0201", 500.0);
    Seat fallback_seat("Z9", SeatClass::ECONOMY, 10.0);
    Seat* selected_seat = &fallback_seat;
    std::ostringstream output;

    const bool prepared =
        rsh::tryPrepareSeatForBooking(output, airplane, customer, "99Z", selected_seat);

    EXPECT_FALSE(prepared);
    EXPECT_EQ(selected_seat, nullptr);
    EXPECT_EQ(output.str(), "Seat 99Z does not exist on this flight.\n");
}

TEST(ReservationSystemHelpersTest, TryPrepareSeatForBookingRejectsBookedSeat) {
    Airplane airplane("FL101", 2, 2);
    Seat* booked_seat = airplane.findSeat("1A");
    ASSERT_NE(booked_seat, nullptr);
    ASSERT_TRUE(booked_seat->bookSeat());

    Customer customer("Booked Seat User", 30, "CUST0202", 500.0);
    Seat* selected_seat = nullptr;
    std::ostringstream output;

    const bool prepared =
        rsh::tryPrepareSeatForBooking(output, airplane, customer, "1A", selected_seat);

    EXPECT_FALSE(prepared);
    EXPECT_EQ(selected_seat, booked_seat);
    EXPECT_EQ(output.str(), "Seat 1A is already booked.\n");
}

TEST(ReservationSystemHelpersTest, TryPrepareSeatForBookingSuggestsLowerPriceSeatsWhenFundsAreInsufficient) {
    Airplane airplane("FL101", 2, 2);
    Customer customer("Low Funds", 31, "CUST0203", 100.0);
    Seat* selected_seat = nullptr;
    std::ostringstream output;

    const bool prepared =
        rsh::tryPrepareSeatForBooking(output, airplane, customer, "1A", selected_seat);

    EXPECT_FALSE(prepared);
    ASSERT_NE(selected_seat, nullptr);
    EXPECT_EQ(selected_seat->getSeatId(), "1A");
    EXPECT_NE(output.str().find("Seat 1A (Business) costs $200"), std::string::npos);
    EXPECT_NE(output.str().find("Insufficient funds. You have $100"), std::string::npos);
    EXPECT_NE(output.str().find("Perhaps one of these seats instead?"), std::string::npos);
    EXPECT_NE(output.str().find("(Economy) costs $50"), std::string::npos);
}

TEST(ReservationSystemHelpersTest, TryPrepareSeatForBookingSelectsSeatWhenCustomerCanAffordIt) {
    Airplane airplane("FL101", 2, 2);
    Customer customer("Ready Buyer", 32, "CUST0204", 500.0);
    Seat* selected_seat = nullptr;
    std::ostringstream output;

    const bool prepared =
        rsh::tryPrepareSeatForBooking(output, airplane, customer, "1A", selected_seat);

    EXPECT_TRUE(prepared);
    ASSERT_NE(selected_seat, nullptr);
    EXPECT_EQ(selected_seat->getSeatId(), "1A");
    EXPECT_EQ(output.str(), "Seat 1A (Business) costs $200\n");
}
