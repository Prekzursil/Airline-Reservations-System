import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { fetchCustomerDetails, cancelBooking as apiCancelBooking } from '../services/apiService';

const renderBookings = (bookings, handleCancelBooking) => {
    if (!bookings || bookings.length === 0) {
        return <p>No bookings found for this customer.</p>;
    }

    return (
        <ul>
            {bookings.map((booking) => (
                <li key={booking.bookingId}>
                    ID: {booking.bookingId}, Flight: {booking.flightNumber}, Seat: {booking.seatId}, Status: {booking.status}
                    {booking.status === 'CANCELLED' ? null : (
                        <button
                            type="button"
                            onClick={() => handleCancelBooking(booking.bookingId)}
                            aria-label={`Cancel booking ${booking.bookingId}`}
                            style={{ marginLeft: '10px' }}
                        >
                            Cancel Booking
                        </button>
                    )}
                </li>
            ))}
        </ul>
    );
};

const CustomerDetails = ({ customerId, onBookingCancelled = null, refreshTrigger = 0 }) => {
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
            setCustomer(null);
        }
    }, [customerId, refreshTrigger]);

    const handleCancelBooking = async (bookingId) => {
        if (!globalThis.confirm(`Are you sure you want to cancel booking ${bookingId}?`)) {
            return;
        }
        setActionStatus(`Cancelling booking ${bookingId}...`);
        try {
            const result = await apiCancelBooking(bookingId);
            setActionStatus(result.message || `Booking ${bookingId} cancellation processed.`);
            if (onBookingCancelled) {
                onBookingCancelled(customerId);
            }
        } catch (err) {
            setActionStatus(`Failed to cancel booking ${bookingId}: ${err.message}`);
        }
    };

    let content = <p>Select or enter a customer ID to view details.</p>;
    if (customerId) {
        if (loading) {
            content = <p>Loading customer details...</p>;
        } else if (error) {
            content = <p style={{ color: 'red' }}>{error}</p>;
        } else if (!customer) {
            content = <p>No customer data found for ID: {customerId}.</p>;
        } else {
            content = (
                <div>
                    <h4>Customer Details: {customer.name} (ID: {customer.personId})</h4>
                    <p>Age: {customer.age}</p>
                    <p>Money: ${customer.money.toFixed(2)}</p>
                    <h5>Bookings:</h5>
                    {renderBookings(customer.bookings, handleCancelBooking)}
                    {actionStatus && <p aria-live="polite"><em>{actionStatus}</em></p>}
                </div>
            );
        }
    }
    return content;
};

CustomerDetails.propTypes = {
    customerId: PropTypes.string,
    onBookingCancelled: PropTypes.func,
    refreshTrigger: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
};

export default CustomerDetails;
