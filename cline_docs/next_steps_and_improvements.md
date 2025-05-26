# Next Steps and Improvements: Airline Reservation System

This document outlines the immediate debugging objectives, current issues, short-term and long-term improvement ideas, and actionable next steps for development sessions.

## Current Phase: Initial Setup & Planning

### Immediate Debugging Objectives:
- N/A (No code written yet to debug).

### List of Specific Issues Currently Being Addressed:
- N/A (No code written yet).

## Actionable Next Steps for Development (Post Memory Bank Setup):

1.  **Create `src` directory:** This will house all C++ source code.
    *   Command: `mkdir src` (or handled by `write_to_file` if creating files directly into `src/`).

2.  **Implement `Person` Class:**
    *   Create `src/Person.h`:
        *   Define class structure with attributes (`name`, `age`, `personId`).
        *   Declare constructors (default, parameterized), virtual destructor.
        *   Declare getters and setters for attributes.
        *   Declare `virtual void displayDetails() const = 0;` (making it an abstract class).
        *   Include necessary headers (`<string>`).
        *   Add include guards.
    *   Create `src/Person.cpp`:
        *   Implement constructors, destructor, getters, and setters.

3.  **Implement `Customer` Class:**
    *   Create `src/Customer.h`:
        *   Define class structure inheriting from `Person`.
        *   Add `money` attribute.
        *   Declare constructors, destructor.
        *   Declare getters and setters for `money`.
        *   Override `displayDetails() const`.
        *   Include `Person.h`.
        *   Add include guards.
    *   Create `src/Customer.cpp`:
        *   Implement constructors, destructor, getters, setters, and `displayDetails()`.

4.  **Implement `Seat` Class:**
    *   Create `src/Seat.h`:
        *   Define `SeatClass` enum (`ECONOMY`, `BUSINESS`).
        *   Define class structure (`seatId`, `isBooked`, `price`, `seatClass`).
        *   Declare constructors, destructor, methods (`book`, `unbook`, `isBooked`, `getPrice`, `getSeatClass`, `getSeatId`).
        *   Add include guards.
    *   Create `src/Seat.cpp`:
        *   Implement all declared methods.

5.  **Implement `Airplane` Class:**
    *   Create `src/Airplane.h`:
        *   Define class structure (`flightNumber`, `seats` (e.g., `std::vector<Seat>`), `bookedSeatsCount`).
        *   Declare constructors (e.g., to initialize with rows/cols to create seats), destructor.
        *   Declare methods (`findSeat`, `displaySeatingMap`, `isFull`, `getAvailableSeats`, `suggestLowerPriceSeats`).
        *   Include `Seat.h`, `<vector>`, `<string>`.
        *   Add include guards.
    *   Create `src/Airplane.cpp`:
        *   Implement methods. Seat initialization logic will be key here.

6.  **Implement `Booking` Class:**
    *   Create `src/Booking.h`:
        *   Define `BookingStatus` enum (`CONFIRMED`, `CANCELLED`).
        *   Define class structure (`bookingId`, `customerId`, `flightNumber`, `seatId`, `bookingDate`, `status`).
        *   Declare constructors, destructor, methods (`getBookingDetails`).
        *   Include `<string>`.
        *   Add include guards.
    *   Create `src/Booking.cpp`:
        *   Implement methods.

7.  **Implement `ReservationSystem` Class:**
    *   Create `src/ReservationSystem.h`:
        *   Define class structure (collections of `Airplane`, `Customer`, `Booking`).
        *   Declare methods for all system operations (add customer, book seat, etc.) and menu handling.
        *   Include necessary class headers, `<vector>`, `<iostream>`, etc.
        *   Add include guards.
    *   Create `src/ReservationSystem.cpp`:
        *   Implement methods. This will contain the bulk of the application logic and user interaction.

8.  **Implement `main.cpp`:**
    *   Create `src/main.cpp`:
        *   Include `ReservationSystem.h`.
        *   Create an instance of `ReservationSystem`.
        *   Call the main run loop/method of the `ReservationSystem`.

9.  **Create Build System:**
    *   Develop a `Makefile` or `CMakeLists.txt` to compile all source files into an executable.

10. **Iterative Testing and Refinement:**
    *   Compile and test frequently after implementing each major piece of functionality.
    *   Debug issues as they arise.

## Short-Term Improvement Ideas (During Initial Development):
-   Implement robust input validation for all user inputs.
-   Add clear and user-friendly console output and error messages.
-   Ensure consistent formatting and adherence to coding style.
-   Develop a simple unique ID generation scheme (e.g., prefix + counter).

## Long-Term Improvement Ideas (Post-Core Functionality):
-   **File I/O:** Implement saving and loading of system state (airplanes, customers, bookings) to/from files for data persistence.
-   **Advanced Seat Management:** More complex seating arrangements, seat features (window, aisle).
-   **Dynamic Pricing:** Prices that change based on demand or time before flight.
-   **User Authentication:** Basic login for different user roles (e.g., admin vs. customer), though likely out of scope.
-   **Reporting:** Generate reports (e.g., list of passengers for a flight, booking statistics).
-   **Enhanced UI:** If allowed and time permits, explore simple GUI libraries (though the requirement is console).
-   **More Detailed Error Handling:** Use custom exceptions for better error management.
-   **Unit Tests:** Introduce unit tests for critical components.

This document will be updated as the project progresses, new issues are found, or new improvement ideas emerge.
