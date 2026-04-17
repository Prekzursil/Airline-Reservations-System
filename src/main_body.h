// cppcheck-suppress-file missingIncludeSystem
#ifndef AIRLINE_MAIN_BODY_H
#define AIRLINE_MAIN_BODY_H

#include "ReservationSystem.h"
#include <iostream>

inline int run_airline_main() {
    std::cout << "Welcome to the Airline Reservation System!" << std::endl;
    std::cout << "Initializing..." << std::endl;

    ReservationSystem airlineSystem;

    std::cout << "Initialization Complete. Starting system..." << std::endl;
    airlineSystem.run();

    std::cout << "Thank you for using the Airline Reservation System." << std::endl;

    return 0;
}

#endif
