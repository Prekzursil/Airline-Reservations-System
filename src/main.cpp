#include "ReservationSystem.h"
#include <iostream>

int main() {
    // Set console output to UTF-8 to support a wider range of characters if needed.
    // This might be platform-specific. For Windows:
    // #if defined(_WIN32) || defined(_WIN64)
    // #include <windows.h>
    // SetConsoleOutputCP(CP_UTF8);
    // #endif

    std::cout << "Welcome to the Airline Reservation System!" << std::endl;
    std::cout << "Initializing..." << std::endl;

    ReservationSystem airlineSystem;
    
    std::cout << "Initialization Complete. Starting system..." << std::endl;
    airlineSystem.run();

    std::cout << "Thank you for using the Airline Reservation System." << std::endl;

    return 0;
}
