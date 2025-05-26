// #define CPPHTTPLIB_OPENSSL_SUPPORT // SSL Support removed for simplicity
#include "../third_party/httplib.h"
#include "../third_party/nlohmann_json.hpp" // Corrected path
#include "ReservationSystem.h"
#include "Airplane.h"
#include "Seat.h"
#include "Customer.h"
#include "Booking.h"
#include <iostream>
#include <vector>
#include <string>
#include <cstdlib> // For rand() in customer auto-generation
#include <ctime>   // For time() in srand()

// Use nlohmann::json
using json = nlohmann::json;

// --- JSON Serialization Functions ---
void to_json(json& j, const Seat& s) {
    j = json{
        {"seatId", s.getSeatId()},
        {"isBooked", s.getIsBooked()},
        {"price", s.getPrice()},
        {"seatClass", s.getSeatClassString()}
    };
    // bookedByCustomerId and bookingId will be added dynamically in the route handler if needed
}

void to_json(json& j, const Airplane& p) {
    // This basic serialization is used by /api/airplanes (list)
    // For /api/airplanes/{id}, we build it manually to include bookedByCustomerId & bookingId
    j = json{
        {"flightNumber", p.getFlightNumber()},
        {"capacity", p.getCapacity()},
        {"bookedSeatsCount", p.getBookedSeatsCount()},
        {"isFull", p.isFull()}
        // "seats" are handled by the specific route if details are needed
    };
}

void to_json(json& j, const Customer& c) {
    j = json{
        {"personId", c.getPersonId()},
        {"name", c.getName()},
        {"age", c.getAge()},
        {"money", c.getMoney()}
        // "bookings" are added dynamically in the route handler
    };
}

void to_json(json& j, const Booking& b) {
    j = json{
        {"bookingId", b.getBookingId()},
        {"customerId", b.getCustomerId()},
        {"flightNumber", b.getFlightNumber()},
        {"seatId", b.getSeatId()},
        {"bookingDate", b.getBookingDateString()},
        {"status", b.getStatusString()}
    };
}

// Helper to set common response headers including CORS
void set_common_headers(httplib::Response& res) {
    res.set_header("Access-Control-Allow-Origin", "*");
    res.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization");
    res.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
}


int main() {
    httplib::Server svr;
    srand(time(nullptr)); 
    
    ReservationSystem airlineSystem(std::cin, std::cout); 

    // --- API Endpoints ---

    svr.Get("/api/airplanes", [&](const httplib::Request& req, httplib::Response& res) {
        (void)req; 
        set_common_headers(res);
        json airplane_list_json = json::array();
        const auto& airplanes = airlineSystem.getAirplanesForTest();
        for (const auto& plane : airplanes) {
            json plane_json_item;
            to_json(plane_json_item, plane); // Basic airplane info
            airplane_list_json.push_back(plane_json_item);
        }
        res.set_content(airplane_list_json.dump(4), "application/json");
    });

    svr.Get(R"(/api/airplanes/(\w+))", [&](const httplib::Request& req, httplib::Response& res) {
        set_common_headers(res);
        std::string flightNumber = req.matches[1];
        Airplane* plane = airlineSystem.findAirplaneByFlightNumber(flightNumber);
        if (plane) {
            json plane_details_json;
            plane_details_json["flightNumber"] = plane->getFlightNumber();
            plane_details_json["capacity"] = plane->getCapacity();
            plane_details_json["bookedSeatsCount"] = plane->getBookedSeatsCount();
            plane_details_json["isFull"] = plane->isFull();
            
            json seats_json_array = json::array();
            const auto& all_plane_seats = plane->getAllSeats(); // This is const std::vector<Seat>&
            const auto& all_bookings = airlineSystem.getBookingsForTest(); 

            for (const auto& seat_obj : all_plane_seats) {
                json seat_json;
                to_json(seat_json, seat_obj); // Basic seat info

                if (seat_obj.getIsBooked()) {
                    for (const auto& booking : all_bookings) {
                        if (booking.getFlightNumber() == plane->getFlightNumber() &&
                            booking.getSeatId() == seat_obj.getSeatId() &&
                            booking.getStatus() == BookingStatus::CONFIRMED) { // Compare enum
                            seat_json["bookedByCustomerId"] = booking.getCustomerId();
                            seat_json["bookingId"] = booking.getBookingId(); 
                            break; 
                        }
                    }
                }
                seats_json_array.push_back(seat_json); // This should be inside the loop for all_plane_seats
            }
            plane_details_json["seats"] = seats_json_array;
            res.set_content(plane_details_json.dump(4), "application/json");
        } else {
            res.status = 404;
            res.set_content(json{{"error", "Airplane not found"}}.dump(4), "application/json");
        }
    });
    
    svr.Get("/api/customers", [&](const httplib::Request& req, httplib::Response& res) {
        (void)req; 
        set_common_headers(res);
        const auto& customers = airlineSystem.getCustomersForTest();
        json customer_list_json = customers; 
        res.set_content(customer_list_json.dump(4), "application/json");
    });

    svr.Get(R"(/api/customers/(\w+))", [&](const httplib::Request& req, httplib::Response& res) {
        set_common_headers(res);
        std::string customerId = req.matches[1];
        Customer* customer = airlineSystem.findCustomerById(customerId);

        if (customer) {
            json customer_json;
            to_json(customer_json, *customer); 
            
            json bookings_json_for_customer = json::array();
            const auto& all_system_bookings = airlineSystem.getBookingsForTest(); 
            for (const auto& booking : all_system_bookings) {
                if (booking.getCustomerId() == customerId) {
                    bookings_json_for_customer.push_back(booking); 
                }
            }
            customer_json["bookings"] = bookings_json_for_customer;
            res.set_content(customer_json.dump(4), "application/json");
        } else {
            res.status = 404;
            res.set_content(json{{"error", "Customer not found"}}.dump(4), "application/json");
        }
    });

    svr.Get("/api/bookings", [&](const httplib::Request& req, httplib::Response& res) {
        (void)req; 
        set_common_headers(res);
        const auto& bookings = airlineSystem.getBookingsForTest();
        json booking_list_json = bookings; 
        res.set_content(booking_list_json.dump(4), "application/json");
    });

    svr.Post("/api/customers", [&](const httplib::Request& req, httplib::Response& res) {
        set_common_headers(res);
        try {
            json j = json::parse(req.body);
            std::string name = j.value("name", "DefaultName"); 
            int age = j.value("age", 0);
            double money = j.value("money", 0.0);
            bool autoGenerate = j.value("autoGenerate", false);
            
            Customer* new_customer = airlineSystem.addCustomerInternal(name, age, money, autoGenerate);
            if (new_customer) {
                json customer_json = *new_customer;
                res.status = 201; 
                res.set_content(customer_json.dump(4), "application/json");
            } else {
                res.status = 500; 
                res.set_content(json{{"error", "Failed to add customer internally"}}.dump(4), "application/json");
            }
        } catch (const std::exception& e) { 
            res.status = 400; 
            res.set_content(json{{"error", "Error processing customer data: " + std::string(e.what())}}.dump(4), "application/json");
        }
    });

    svr.Post("/api/bookings", [&](const httplib::Request& req, httplib::Response& res) {
        set_common_headers(res);
        try {
            json j = json::parse(req.body);
            std::string customerId = j.at("customerId").get<std::string>();
            std::string flightNumber = j.at("flightNumber").get<std::string>();
            std::string seatId = j.at("seatId").get<std::string>();
            std::string error_message;

            Booking* new_booking = airlineSystem.createBookingInternal(customerId, flightNumber, seatId, error_message);
            
            if (new_booking) {
                json booking_json = *new_booking; 
                res.status = 201; 
                res.set_content(booking_json.dump(4), "application/json");
            } else {
                if (error_message.find("not found") != std::string::npos) res.status = 404; 
                else if (error_message.find("already booked") != std::string::npos) res.status = 409; 
                else if (error_message.find("Insufficient funds") != std::string::npos) res.status = 402; 
                else res.status = 400; 
                res.set_content(json{{"error", error_message}}.dump(4), "application/json");
            }
        } catch (const std::exception& e) {
            res.status = 400; 
            res.set_content(json{{"error", "Error processing booking data: " + std::string(e.what())}}.dump(4), "application/json");
        }
    });

    svr.Delete(R"(/api/bookings/([A-Za-z0-9\-]+))", [&](const httplib::Request& req, httplib::Response& res) {
        set_common_headers(res);
        std::string bookingId = req.matches[1];
        std::string error_message;
        bool success = airlineSystem.cancelBookingInternal(bookingId, error_message);
        if (success) {
            res.set_content(json{{"message", error_message}}.dump(4), "application/json");
        } else {
            if (error_message.find("not found") != std::string::npos) res.status = 404;
            else if (error_message.find("already cancelled") != std::string::npos) res.status = 409;
            else res.status = 500; 
            res.set_content(json{{"error", error_message}}.dump(4), "application/json");
        }
    });

    svr.Post("/api/bookings/swap", [&](const httplib::Request& req, httplib::Response& res) {
        set_common_headers(res);
        try {
            json j = json::parse(req.body);
            std::string bookingId1 = j.at("bookingId1").get<std::string>();
            std::string bookingId2 = j.at("bookingId2").get<std::string>();
            std::string error_message;
            bool success = airlineSystem.swapSeatsInternal(bookingId1, bookingId2, error_message);
            if (success) {
                res.set_content(json{{"message", error_message}}.dump(4), "application/json");
            } else {
                 if (error_message.find("not found") != std::string::npos || error_message.find("not confirmed") != std::string::npos) res.status = 404;
                 else if (error_message.find("Cannot swap a booking with itself") != std::string::npos || 
                          error_message.find("only supported for bookings on the same flight") != std::string::npos) res.status = 400;
                 else res.status = 500; 
                res.set_content(json{{"error", error_message}}.dump(4), "application/json");
            }
        } catch (const std::exception& e) {
            res.status = 400; 
            res.set_content(json{{"error", "Error processing seat swap request: " + std::string(e.what())}}.dump(4), "application/json");
        }
    });
    
    svr.Options(R"((.*))", [](const httplib::Request& req, httplib::Response& res) {
        (void)req; 
        set_common_headers(res); 
        res.status = 204;
    });
    
    svr.set_base_dir("./"); 
    svr.set_logger([](const httplib::Request& req, const httplib::Response& res) {
        std::cout << "HTTP " << req.method << " " << req.path << " -> " << res.status << std::endl;
    });
    
    std::cout << "Starting API server on http://localhost:8080..." << std::endl;
    if (!svr.listen("0.0.0.0", 8080)) {
         std::cerr << "Failed to start server!" << std::endl;
         return 1;
    }

    return 0;
}
