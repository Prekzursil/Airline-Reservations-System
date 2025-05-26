# Product Context: Airline Reservation System

## Why This Project Exists
This project is an assignment for an Object-Oriented Programming (OOP) course. The primary goal is to apply OOP principles and methodologies to solve a real-world problem.

## What Problems It Solves
The project aims to simulate a basic airline reservation system, allowing for the management of:
- Airplanes and their seating capacity.
- Customers and their ability to book flights.
- Different classes of seats (e.g., Business, Economy) with varying prices.
- Basic booking operations like creating bookings, searching for customers, swapping seats, and cancelling bookings.

## How It Should Work
The system will be a C++ console-based application. Users will interact with it through a menu-driven interface.

Key functionalities include:
- **Customer Management:**
    - Creating new customers (manually or automatically generated with attributes like name, age, ID, and initial funds).
- **Flight and Seat Management:**
    - Defining airplanes with specific flight numbers and seating configurations (rows, seats per row).
    - Seats will have unique IDs (e.g., "1A"), a class (Economy/Business), a price, and a booking status.
- **Booking Process:**
    - Customers can choose and attempt to buy a specific seat on a flight.
    - The system will check if the customer has sufficient funds.
    - If a chosen seat is too expensive, the system can suggest lower-priced alternatives.
    - Successful bookings will link a customer to a seat on a specific flight.
- **System Operations:**
    - Asserting if a plane is filled and rejecting further customers if so.
    - Searching for customers by ID or name.
    - Swapping seats between two customers.
    - Removing/cancelling the booking of a customer.
- **Output:**
    - Displaying seating maps.
    - Providing feedback on operations (e.g., booking confirmation, errors).

The system must adhere to OOP principles:
- At least 3 classes.
- Inheritance.
- Constructors and Destructors.
- Encapsulation (public, private, protected).
- Method Overloading and/or Overriding.
- Getters and Setters.
- Modular design (separate .h and .cpp files for classes).
- Potential use of abstract classes and interfaces for extensibility.
