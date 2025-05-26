# Technical Context: Airline Reservation System

This document details the technologies, development environment, and technical constraints for the Airline Reservation System project.

## Core Technology
- **Programming Language:** C++ (Standard: C++11 or newer, to allow for features like `enum class`, range-based for loops, smart pointers if desired, though initial implementation will stick to basics as per typical course requirements unless advanced features are explicitly requested or become necessary).
- **Compiler:** A standard C++ compiler like g++ (MinGW for Windows) or Clang will be assumed. The code should be written to be as platform-independent as possible within the console environment.

## Development Environment
- **IDE/Editor:** Not specified, but the code will be structured to be compatible with common C++ IDEs (like Visual Studio, CLion, VS Code with C++ extensions) or simple text editors with command-line compilation.
- **Operating System:** The application will be a console application, expected to run on common desktop operating systems (Windows, macOS, Linux).
- **Build System:** Initially, manual compilation via g++ commands might be used. A `Makefile` or a simple `CMakeLists.txt` is planned for easier compilation as the project grows with multiple source files.
    - Example g++ compilation for a single file: `g++ main.cpp -o airline_reservation`
    - Example g++ compilation for multiple files: `g++ main.cpp Person.cpp Customer.cpp Seat.cpp Airplane.cpp Booking.cpp ReservationSystem.cpp -o airline_reservation -std=c++11`

## Standard Library Usage
The project will make extensive use of the C++ Standard Library, including:
- **Input/Output:** `<iostream>` for console I/O ( `std::cin`, `std::cout`).
- **Strings:** `<string>` for `std::string`.
- **Containers:** `<vector>` for `std::vector`. Other containers like `<map>` or `<list>` might be considered if specific needs arise, but `std::vector` will be the default.
- **Algorithms:** `<algorithm>` for sorting or searching if needed (e.g., `std::sort`, `std::find_if`).
- **Utilities:** `<limits>` for input validation, `<iomanip>` for formatted output if necessary.

## Project Structure
- **Source Files:** Code will be organized into `.h` (header) and `.cpp` (implementation) files for each class.
- **`src` Directory:** All source code will reside in a `src/` directory to keep the project root clean.
- **`cline_docs` Directory:** For all Memory Bank documentation.

## Coding Conventions and Style
- **Naming:**
    - Classes: `PascalCase` (e.g., `ReservationSystem`).
    - Methods/Functions: `camelCase` (e.g., `bookSeat`).
    - Variables: `camelCase` (e.g., `flightNumber`).
    - Constants/Enums: `UPPER_SNAKE_CASE` (e.g., `MAX_CAPACITY`, `ECONOMY`).
- **Indentation:** Consistent indentation (e.g., 4 spaces or tabs, to be decided, but will be consistent).
- **Comments:**
    - Header files will have comments explaining the purpose of the class and its public members.
    - Implementation files will have comments for complex logic or non-obvious sections.
- **Include Guards:** All header files will use include guards (`#ifndef CLASS_NAME_H`, `#define CLASS_NAME_H`, `#endif`) to prevent multiple inclusion issues.

## Technical Constraints & Requirements (from PDF)
- **OOP Constructs:** Must use inheritance, constructors/destructors, access specifiers (public/private/protected), method overloading/overriding, getters/setters.
- **Minimum 3 Classes:** The current plan exceeds this.
- **Console Output:** The project is designed with console display as the primary output.
- **No AI Usage:** The project must be developed without AI assistance for coding.
- **Maintainability, Extensibility, Overall Design:** These are key grading criteria, influencing the modular structure and adherence to OOP best practices.

## Future Considerations (Optional)
- **Error Handling:** More robust error handling mechanisms (e.g., custom exception classes) could be implemented if the project complexity grows significantly.
- **File I/O:** For persistence, data could be saved to and loaded from files (e.g., CSV, JSON, or binary). This is currently out of scope for the initial version but a common extension.
- **Unit Testing:** For a larger project, a unit testing framework (like Google Test) would be beneficial. This is likely out of scope for this assignment.
