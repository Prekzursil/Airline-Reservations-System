# File Tree: Airline Reservation System

This document will map out the file and folder structure of the Airline Reservation System project. It will be updated as new files and directories are created.

## Project File Structure

```
OOP_C++_cirstina/
├── cline_docs/
│   ├── productContext.md
│   ├── activeContext.md
│   ├── fileTree.md
│   ├── systemPatterns.md
│   ├── techContext.md
│   ├── progress.md
│   └── next_steps_and_improvements.md
├── src/
│   ├── Person.h
│   ├── Person.cpp
│   ├── Customer.h
│   ├── Customer.cpp
│   ├── Seat.h
│   ├── Seat.cpp
│   ├── Airplane.h
│   ├── Airplane.cpp
│   ├── Booking.h
│   ├── Booking.cpp
│   ├── ReservationSystem.h
│   ├── ReservationSystem.cpp
│   ├── main.cpp
│   └── api_server_main.cpp
├── airline_reservation_system.exe  # Compiled console application
├── airline_api_server.exe      # Compiled API server
├── run_console_app.bat         # Batch file to run console app
├── run_gui_app.bat             # Batch file to run GUI app
├── airline-gui/                # React frontend application
│   ├── node_modules/           # (Typically not committed)
│   ├── public/
│   │   └── index.html
│   │   └── ... (other public assets)
│   ├── src/
│   │   ├── components/
│   │   │   ├── FlightList.js
│   │   │   ├── SeatMap.js
│   │   │   └── CustomerForm.js
│   │   ├── services/
│   │   │   └── apiService.js
│   │   ├── App.css
│   │   ├── App.js
│   │   ├── App.test.js
│   │   ├── index.css
│   │   ├── index.js
│   │   └── ... (other React source files)
│   ├── .gitignore
│   ├── package.json
│   └── README.md
├── Makefile
└── OOP Projects_2025_v2_b9e270fe47ae4d1048db4ac662e69200.pdf

```

### File Descriptions:

*   **`src/Person.h`**: Header file for the `Person` base class.
    *   Dependencies: None initially.
*   **`src/Person.cpp`**: Implementation file for the `Person` base class.
    *   Dependencies: `Person.h`.
*   **`src/Customer.h`**: Header file for the `Customer` class.
    *   Dependencies: `Person.h`.
*   **`src/Customer.cpp`**: Implementation file for the `Customer` class.
    *   Dependencies: `Customer.h`.
*   **`src/Seat.h`**: Header file for the `Seat` class.
    *   Dependencies: Enum for `SeatClass`.
*   **`src/Seat.cpp`**: Implementation file for the `Seat` class.
    *   Dependencies: `Seat.h`.
*   **`src/Airplane.h`**: Header file for the `Airplane` class.
    *   Dependencies: `Seat.h`, `Customer.h` (for suggesting seats).
*   **`src/Airplane.cpp`**: Implementation file for the `Airplane` class.
    *   Dependencies: `Airplane.h`.
*   **`src/Booking.h`**: Header file for the `Booking` class.
    *   Dependencies: Enum for `BookingStatus`.
*   **`src/Booking.cpp`**: Implementation file for the `Booking` class.
    *   Dependencies: `Booking.h`.
*   **`src/ReservationSystem.h`**: Header file for the `ReservationSystem` class.
    *   Dependencies: `Airplane.h`, `Customer.h`, `Booking.h`.
*   **`src/ReservationSystem.cpp`**: Implementation file for the `ReservationSystem` class.
    *   Dependencies: `ReservationSystem.h`, `iostream`, `vector`, `string`, etc.
*   **`src/main.cpp`**: Main entry point for the console application.
    *   Dependencies: `ReservationSystem.h`.
*   **`src/api_server_main.cpp`**: Main entry point for the HTTP API server.
    *   Dependencies: `ReservationSystem.h`, `httplib.h`, `nlohmann_json.hpp`.
*   **`Makefile`**: Build script for compiling the project (console app, API server, tests).
