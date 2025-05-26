# Airline Reservation System

## 1. Project Overview

This project implements an Airline Reservation System using C++ for the backend logic and a React-based web interface for the graphical user interface (GUI). The system demonstrates Object-Oriented Programming (OOP) principles, modular design, and provides functionalities for managing customers, flights, seats, and bookings.

**Core Features:**
- **Customer Management:** Add new customers (manually or auto-generated), view customer details, and see their bookings.
- **Flight Management:** View available flights, display detailed seat maps, and see seat availability.
- **Booking Management:** Book specific seats for customers, cancel existing bookings (with refunds), and swap seats between two bookings.
- **Seat Information:** View seat class (Economy, Business), price, and booking status. For booked seats, view the customer ID of the occupant and cancel the booking directly from the seat map.
- **Dual Interface:**
    - **Console Application:** A command-line interface (CLI) for interacting with the system.
    - **Graphical User Interface (GUI):** A web-based React application interacting with a C++ backend API server.

## 2. Requirements

### 2.1. C++ Backend & Console Application:
- **C++ Compiler:** A C++17 compatible compiler (e.g., g++/MinGW).
- **Make:** A build automation tool like `mingw32-make` (for Windows with MinGW) or `make` (for Linux/macOS).
- **Googletest (for tests):** The project includes Googletest as a third-party library. It's set up to be compiled with the tests.

### 2.2. C++ API Server (for GUI):
- Same as C++ Backend.
- **cpp-httplib:** Included as a third-party header-only library for the HTTP server.
- **nlohmann/json:** Included as a third-party header-only library for JSON parsing/serialization.

### 2.3. React GUI Frontend:
- **Node.js and npm:** Required to install dependencies and run the React development server. (Node.js version 14.x or higher recommended).

## 3. Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  **C++ Dependencies:**
    - The third-party libraries (`cpp-httplib`, `nlohmann/json`, `googletest`) are included in the `third_party/` directory. No separate installation is typically needed if they are correctly referenced by the Makefile.
3.  **React Frontend Dependencies:**
    Navigate to the `airline-gui` directory and install npm packages:
    ```bash
    cd airline-gui
    npm install
    cd .. 
    ```

## 4. Building and Running the Application

The project provides batch scripts (`.bat` files) for easier building and running on Windows. For other operating systems, you can adapt the commands from these scripts or use the Makefile directly.

### 4.1. C++ Console Application

-   **To Build, Test, and Run:**
    Execute the `run_console_app.bat` script from the project root directory:
    ```bash
    .\run_console_app.bat
    ```
    This script will:
    1.  Clean previous builds.
    2.  Compile the main application (`airline_reservation_system.exe`).
    3.  Compile and run all C++ unit tests (`run_tests_executable.exe`).
    4.  If tests pass, it will launch the console application.

-   **Manual Compilation (using Makefile):**
    ```bash
    mingw32-make airline_reservation_system  # Build the console app
    mingw32-make tests                     # Build and run tests
    ./airline_reservation_system.exe       # Run the console app
    ```

### 4.2. GUI Application (React Frontend + C++ API Server)

-   **To Build, Test C++ components, Start API Server, and Start React Frontend:**
    Execute the `run_gui_app.bat` script from the project root directory:
    ```bash
    .\run_gui_app.bat
    ```
    This script will:
    1.  Clean previous C++ builds.
    2.  Compile the C++ API server (`airline_api_server.exe`).
    3.  Compile and run all C++ unit tests.
    4.  If tests pass, it will start the C++ API server in a new console window. (Keep this window open; API runs on `http://localhost:8080`).
    5.  Navigate into `airline-gui` and run `npm start` to launch the React development server. This usually opens the GUI in your default web browser at `http://localhost:3000`.

-   **Manual Steps:**
    1.  **Build and Run C++ API Server:**
        ```bash
        mingw32-make airline_api_server
        .\airline_api_server.exe 
        ```
        (Keep this server running in a terminal).
    2.  **Run React Frontend:**
        Open a new terminal, navigate to the `airline-gui` directory:
        ```bash
        cd airline-gui
        npm start
        ```

## 5. How to Use the Application

### 5.1. Console Application

Once `airline_reservation_system.exe` is running, you'll be presented with a main menu:

```
===== Airline Reservation System Menu =====
1. Add New Customer
2. Book a Seat
3. View Flight Details (Seating Map, Available Seats)
4. Search Customer
5. Cancel Booking
6. Swap Seats
7. Admin Options
0. Exit
=========================================
Enter your choice:
```

-   **1. Add New Customer:** Allows adding a customer manually (name, age, initial money) or automatically generating one.
-   **2. Book a Seat:**
    -   Select a customer by ID.
    -   Select an available flight.
    -   View the seat map and available seats for the chosen flight.
    -   Enter a seat ID to book.
    -   The system checks for seat availability and customer funds.
    -   Suggests cheaper seats if the selected one is too expensive.
-   **3. View Flight Details:** Select a flight to see its seating map (X for booked, B for Business, E for Economy) and a list of all available seats with details.
-   **4. Search Customer:** Enter a customer ID to view their details (name, age, money) and a list of their confirmed bookings.
-   **5. Cancel Booking:** Enter a booking ID to cancel it. The seat becomes available, and the customer is refunded.
-   **6. Swap Seats:** Enter two booking IDs (must be on the same flight) to swap their assigned seats.
-   **7. Admin Options:**
    -   Add a new airplane (flight number, rows, seats per row).
    -   View all customers in the system.
    -   View all bookings in the system.
-   **0. Exit:** Terminates the application.

### 5.2. GUI Application

Ensure both the C++ API server (`http://localhost:8080`) and the React development server (`http://localhost:3000`) are running. Open `http://localhost:3000` in your web browser.

The GUI is divided into two main sections: **Customer Management** and **Flight & Booking Management**.

**Customer Management:**
-   **Add New Customer:**
    -   Fill in the name, age, and money, or check "Auto-generate customer data".
    -   Click "Add Customer". The new customer will appear in the "All Customers" list.
-   **Refresh Customer List:** Fetches and displays the latest list of all customers.
-   **All Customers:** Lists all customers. Clicking a customer's name will populate their ID in the "View Specific Customer Details" search box and load their details.
-   **View Specific Customer Details:**
    -   Enter a Customer ID and click "Search Customer".
    -   Displays the customer's details (name, age, money) and their active bookings.
    -   Each booking has a "Cancel Booking" button. Clicking it will cancel the booking and update the list.

**Flight & Booking Management:**
-   **Available Flights:**
    -   Lists all available flights with capacity and booked count.
    -   Click a flight button to view its details and seat map. Clicking again hides the details.
-   **Details for Flight (Seat Map):**
    -   Displays a visual seat map:
        -   Green: Available Economy
        -   Light Blue: Available Business
        -   Red: Booked
        -   Yellow: Currently selected by you for booking
    -   **Booking a Seat:**
        1.  Select an available (green or light blue) seat by clicking on it. It will turn yellow.
        2.  The status message below the map will show details of the selected seat.
        3.  Choose a customer from the filterable "Select Customer" dropdown.
        4.  Click "Confirm Booking for [SeatID]".
        5.  A success or failure message will appear. The seat map and flight list will update.
    -   **Viewing Booked Seat Info / Cancelling from Seat Map:**
        1.  Click on a booked (red) seat.
        2.  The status message will show "Booked by: [CustomerID]" and "Booking ID: [BookingID]".
        3.  A small "Cancel" button will appear directly on the seat. Clicking this button will prompt for confirmation and then cancel the booking. The UI will update.
-   **Swap Seats Between Two Bookings:**
    -   This section allows swapping seats for two existing, confirmed bookings.
    -   Use the two filterable dropdowns ("Select Booking 1...", "Select Booking 2...") to choose the bookings. The dropdowns list all confirmed bookings with details (Booking ID, Customer ID, Flight, Seat).
    -   Once two different bookings are selected, the "Swap Selected Seats" button becomes enabled.
    -   Clicking it performs the swap. The booking list in these dropdowns will refresh automatically.

## 6. Project Structure

(Refer to `cline_docs/fileTree.md` for a detailed file tree.)

-   `src/`: Contains all C++ source (.cpp) and header (.h) files for the core logic and API server.
-   `tests/`: Contains C++ unit tests using Googletest.
-   `airline-gui/`: Contains the React frontend application.
    -   `airline-gui/src/components/`: React components.
    -   `airline-gui/src/services/`: Service for API calls (`apiService.js`).
-   `third_party/`: Contains third-party libraries (httplib, nlohmann_json, googletest).
-   `obj/`: Build artifacts (object files, gcov files).
-   `cline_docs/`: Cline's Memory Bank documentation.
-   `Makefile`: For building the C++ parts.
-   `*.bat`: Batch scripts for convenience on Windows.

## 7. Known Issues / Future Improvements

(Refer to `cline_docs/next_steps_and_improvements.md` for a more detailed list.)

-   **Error Handling:** API error messages could be more uniformly structured. Frontend could display errors more gracefully (e.g., toasts).
-   **UI/UX:** General styling and responsiveness of the GUI can be improved.
-   **Advanced Features:** Implement features like user accounts, payment integration, different airplane layouts, etc.
-   **Coverage:** Increase C++ test coverage, especially for `ReservationSystem.cpp` console interaction paths.
