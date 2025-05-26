import React, { useState, useEffect } from 'react';
import { fetchCustomerDetails, cancelBooking as apiCancelBooking } from '../services/apiService';

const CustomerDetails = ({ customerId, onBookingCancelled }) => {
    const [customer, setCustomer] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [actionStatus, setActionStatus] = useState('');

    useEffect(() => {
        if (customerId) {
            const loadDetails = async () => {
                setLoading(true);
                setError('');
                setActionStatus('');
                try {
                    const data = await fetchCustomerDetails(customerId);
                    setCustomer(data);
                } catch (err) {
                    setError(`Failed to load details for customer ${customerId}: ${err.message}`);
                    setCustomer(null);
                } finally {
                    setLoading(false);
                }
            };
            loadDetails();
        } else {
            setCustomer(null); // Clear if no customerId
        }
    }, [customerId]);

    const handleCancelBooking = async (bookingId) => {
        if (!window.confirm(`Are you sure you want to cancel booking ${bookingId}?`)) {
            return;
        }
        setActionStatus(`Cancelling booking ${bookingId}...`);
        try {
            const result = await apiCancelBooking(bookingId);
            setActionStatus(result.message || `Booking ${bookingId} cancellation processed.`);
            // Refresh customer details to show updated booking status and money
            if (onBookingCancelled) onBookingCancelled(customerId); 
        } catch (err) {
            setActionStatus(`Failed to cancel booking ${bookingId}: ${err.message}`);
        }
    };

    if (!customerId) {
        return <p>Select or enter a customer ID to view details.</p>;
    }
    if (loading) {
        return <p>Loading customer details...</p>;
    }
    if (error) {
        return <p style={{ color: 'red' }}>{error}</p>;
    }
    if (!customer) {
        return <p>No customer data found for ID: {customerId}.</p>;
    }

    return (
        <div>
            <h4>Customer Details: {customer.name} (ID: {customer.personId})</h4>
            <p>Age: {customer.age}</p>
            <p>Money: ${customer.money.toFixed(2)}</p>
            <h5>Bookings:</h5>
            {customer.bookings && customer.bookings.length > 0 ? (
                <ul>
                    {customer.bookings.map(booking => (
                        <li key={booking.bookingId}>
                            ID: {booking.bookingId}, Flight: {booking.flightNumber}, Seat: {booking.seatId}, Status: {booking.status}
                            {booking.status !== "CANCELLED" && (
                                <button 
                                    onClick={() => handleCancelBooking(booking.bookingId)} 
                                    style={{ marginLeft: '10px' }}
                                >
                                    Cancel Booking
                                </button>
                            )}
                        </li>
                    ))}
                </ul>
            ) : (
                <p>No bookings found for this customer.</p>
            )}
            {actionStatus && <p><em>{actionStatus}</em></p>}
        </div>
    );
};

export default CustomerDetails;
