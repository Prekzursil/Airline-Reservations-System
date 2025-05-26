# Progress: Airline Reservation System

This document tracks the development progress of the Airline Reservation System.

## Current Status: Core Implementation Complete (Phase 1)

**Date:** 2025-05-26 (Updated after initial core implementation)

### What Works:
- **Memory Bank Documentation:**
    - All initial Memory Bank documents (`productContext.md`, `activeContext.md`, `fileTree.md`, `systemPatterns.md`, `techContext.md`, `progress.md`, `next_steps_and_improvements.md`) are created and populated.
- **Core Application Logic (C++):**
    - **Classes Implemented:**
        - `Person.h`, `Person.cpp` (Abstract base class)
        - `Customer.h`, `Customer.cpp` (Derived from Person)
        - `Seat.h`, `Seat.cpp` (Includes `SeatClass` enum)
        - `Airplane.h`, `Airplane.cpp` (Manages `Seat` objects)
        - `Booking.h`, `Booking.cpp` (Includes `BookingStatus` enum)
        - `ReservationSystem.h`, `ReservationSystem.cpp` (Main controller, menu logic)
        - `main.cpp` (Application entry point)
    - **Functionalities Implemented (Basic versions):**
        - Customer creation (manual input).
        - Airplane initialization with seats.
        - Seat booking process (customer selection, flight selection, seat selection, payment check).
        - Suggestion of lower-priced seats if initial choice is too expensive.
        - Viewing flight details (seating map, available seats).
        - Searching for customers by ID and viewing their details/bookings.
        - Cancelling bookings (with refund and seat unbooking).
        - Basic admin options (add airplane, view all customers/bookings).
        - Console menu and user interaction loop.
    - **Build System:**
        - `Makefile` created for g++ compilation.
        - Project compiles successfully using direct g++ command (as `make` was not found).
        - A signed/unsigned comparison warning in `Airplane.cpp` was fixed.

### What's Left to Build (Key Features & Refinements):

1.  **Robust Error Handling & Input Validation:**
    *   Enhance input validation in all menu handlers (e.g., for string inputs, more complex scenarios).
    *   Provide more descriptive error messages.
2.  **Code Review and Refinements:**
    *   Review `const_cast` usage in `Airplane.cpp` (coverage 95.19%).
    *   Address compiler warnings for unused variables in `ReservationSystem.cpp` (currently due to commented-out display calls).
    *   Ensure full adherence to all OOP principles mentioned in the PDF.
    *   Improve comments and code clarity where needed.
3.  **Thorough Manual/Integration Testing:** Systematically test all menu options and user flows.

### Implemented Features (Post Initial Core):
- **`handleSwapSeats()`:** Implemented in `ReservationSystem.cpp`.
- **Automatic Customer Generation:** Added option in `handleAddCustomer`.
- **I/O Injection for `ReservationSystem`:** Refactored to allow `std::istream` and `std::ostream` injection for improved testability.
- **C++ API Backend (Initial Version):**
    - Created `api_server_main.cpp` using `httplib.h` and `nlohmann/json.hpp`.
    - Implemented basic API endpoints:
        - `GET /api/airplanes`
        - `GET /api/airplanes/{flightNumber}`
        - `GET /api/customers`
        - `POST /api/customers` (simulated addition)
        - `POST /api/bookings` (simulated booking)
    - Added JSON serialization for core classes.
    - Updated `Makefile` to build `airline_api_server.exe`.
- **React Frontend (Initial Structure):**
    - Created `airline-gui` project using `create-react-app`.
    - Implemented `apiService.js` for backend communication.
    - Created basic components: `FlightList.js`, `SeatMap.js`, `CustomerForm.js`.
    - Updated `App.js` to integrate these components.
- **Launcher Scripts:**
    - Created `run_console_app.bat` to build, test, and run the C++ console application.
    - Created `run_gui_app.bat` to build C++ API server, test, start API server, and start React frontend.
- **API Backend Refinement (Partial):**
    - `ReservationSystem` refactored with `addCustomerInternal`, `createBookingInternal`, `cancelBookingInternal`, and `swapSeatsInternal` methods for programmatic access.
    - `api_server_main.cpp` updated to use these internal methods, making `POST /api/customers`, `POST /api/bookings`, `DELETE /api/bookings/{id}`, and `POST /api/bookings/swap` functional.
    - Added `GET /api/customers/{id}` endpoint.
- **React Frontend Enhancements:**
    - `apiService.js` updated with functions for all new API endpoints.
    - `SeatMap.js` updated for functional booking via API.
    - `CustomerDetails.js` component created to display customer info, bookings, and allow booking cancellation.
    - `SwapSeatsForm.js` component created for seat swaps.
    - `App.js` updated to integrate these new components and functionalities.
- **C++ Unit Tests:**
    - Added tests for `cancelBookingInternal` and `swapSeatsInternal` in `ReservationSystemTest`.
- **C++ Compiler Warnings:** Addressed unused variable/parameter warnings in `ReservationSystem.cpp` and `api_server_main.cpp`.
- **Makefile Coverage Target:** Improved `gcov` command for Windows compatibility; `.gcov` files are now generated.
- **Const Correctness:** Addressed `const_cast` in `Airplane.cpp` by changing return types to `std::vector<const Seat*>` and updating relevant test files.
- **All C++ Unit Tests Pass:** All 73 tests are confirmed passing.
- **React GUI QoL Improvements:**
    - `SeatMap.js`:
        - Customer selection for booking uses `react-select` (filterable dropdown).
        - Booked seats are clickable to show occupant info (Customer ID & Booking ID) and offer a "Cancel" button.
        - Business seat colors corrected.
    - `SwapSeatsForm.js`:
        - Uses `react-select` for filterable dropdowns of all confirmed bookings.
        - List of bookings in dropdowns refreshes automatically after new bookings/cancellations/swaps elsewhere in the app.
    - `FlightList.js`: UI updates more smoothly after a booking without closing the flight details view.
- **C++ API Enhancements:**
    - `GET /api/airplanes/{flightNumber}` now includes `bookedByCustomerId` and `bookingId` in seat data.
    - New `GET /api/bookings` endpoint added to list all bookings.
- **Documentation:**
    - `README.md` created with comprehensive project overview, setup, build/run instructions, and usage guide for both console and GUI.

### Progress Status:
- **Overall Project Completion:** All core C++ and React features implemented as per user requests. System is fully functional, unit tested, and documented with a README.
- **Current Phase:** Project Complete.
    - `Airplane.cpp`: 95.19%
    - `Booking.cpp`: 100.00%
    - `Customer.cpp`: 100.00%
    - `Person.cpp`: 90.91%
    - `ReservationSystem.cpp`: 54.92%
    - `Seat.cpp`: 100.00%
    - **Overall Line Coverage (src/*.cpp excluding api_server_main.cpp): ~71.47%** (Based on gcov output).
- **Next Phase:** None. Project requirements met.

This file will be updated regularly to reflect the current state of the project.
