const API_BASE_URL = 'http://localhost:8080/api';

export const fetchAirplanes = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/airplanes`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Failed to fetch airplanes:", error);
        throw error;
    }
};

export const fetchAirplaneDetails = async (flightNumber) => {
    try {
        const response = await fetch(`${API_BASE_URL}/airplanes/${flightNumber}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Failed to fetch details for flight ${flightNumber}:`, error);
        throw error;
    }
};

export const fetchCustomers = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/customers`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Failed to fetch customers:", error);
        throw error;
    }
};

export const addCustomer = async (customerData) => {
    try {
        const response = await fetch(`${API_BASE_URL}/customers`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(customerData),
        });
        if (!response.ok) {
            // Try to parse error body if available
            const errorBody = await response.json().catch(() => ({ error: "Unknown error occurred" }));
            throw new Error(`HTTP error! status: ${response.status} - ${errorBody.error}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Failed to add customer:", error);
        throw error;
    }
};

export const createBooking = async (bookingData) => {
    try {
        const response = await fetch(`${API_BASE_URL}/bookings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(bookingData),
        });
        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({ error: "Unknown error occurred" }));
            throw new Error(`HTTP error! status: ${response.status} - ${errorBody.error}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Failed to create booking:", error);
        throw error;
    }
};

export const fetchCustomerDetails = async (customerId) => {
    try {
        const response = await fetch(`${API_BASE_URL}/customers/${customerId}`);
        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({ error: "Unknown error occurred" }));
            throw new Error(`HTTP error! status: ${response.status} - ${errorBody.error}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Failed to fetch details for customer ${customerId}:`, error);
        throw error;
    }
};

export const cancelBooking = async (bookingId) => {
    try {
        const response = await fetch(`${API_BASE_URL}/bookings/${bookingId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({ error: "Unknown error occurred" }));
            throw new Error(`HTTP error! status: ${response.status} - ${errorBody.error}`);
        }
        return await response.json(); // Or handle empty response if API returns 204
    } catch (error) {
        console.error(`Failed to cancel booking ${bookingId}:`, error);
        throw error;
    }
};

export const fetchBookings = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/bookings`);
        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({ error: "Unknown error occurred" }));
            throw new Error(`HTTP error! status: ${response.status} - ${errorBody.error}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Failed to fetch bookings:", error);
        throw error;
    }
};

export const swapSeats = async (bookingId1, bookingId2) => {
    try {
        const response = await fetch(`${API_BASE_URL}/bookings/swap`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ bookingId1, bookingId2 }),
        });
        if (!response.ok) {
            const errorBody = await response.json().catch(() => ({ error: "Unknown error occurred" }));
            throw new Error(`HTTP error! status: ${response.status} - ${errorBody.error}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Failed to swap seats:", error);
        throw error;
    }
};
