// cppcheck-suppress-file missingIncludeSystem
#include "ReservationSystem.h"
#include <iostream>

int main() {
    std::cout << "Welcome to the Airline Reservation System!" << std::endl;
    std::cout << "Initializing..." << std::endl;

    ReservationSystem airlineSystem;
    
    std::cout << "Initialization Complete. Starting system..." << std::endl;
    airlineSystem.run();

    std::cout << "Thank you for using the Airline Reservation System." << std::endl;

    return 0;
}
