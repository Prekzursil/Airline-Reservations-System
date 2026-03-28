import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import Select from 'react-select';
import { createBooking, fetchCustomers, cancelBooking as apiCancelBooking } from '../services/apiService';

const validateBookingSelection = (selectedSeatId, customerIdForBooking) => {
    if (!selectedSeatId) {
        return 'Please select a seat first.';
    }
    if (!customerIdForBooking?.value) {
        return 'Please select a Customer for booking.';
    }
    return null;
};

const applyBookingValidationError = (selectedSeatId, customerIdForBooking, setBookingStatus) => {
    const validationError = validateBookingSelection(selectedSeatId, customerIdForBooking);
    if (!validationError) {
        return false;
    }
    setBookingStatus(validationError);
    return true;
};

const resolveSeatBackgroundColor = (seat, selectedSeatId) => {
    let backgroundColor = 'lightgreen';
    if (seat.isBooked) {
        backgroundColor = 'lightcoral';
    } else if (seat.seatClass === 'Business') {
        backgroundColor = 'lightblue';
    }

    if (seat.seatId === selectedSeatId) {
        backgroundColor = 'yellow';
    }
    return backgroundColor;
};

const seatMapInternals = {
    applyBookingValidationError,
    resolveSeatBackgroundColor,
    validateBookingSelection
};

const SeatMap = ({ seats, flightNumber, onBookingSuccess = null }) => {
    const [selectedSeatId, setSelectedSeatId] = useState(null);
    const [bookingStatus, setBookingStatus] = useState('');
    const [customerIdForBooking, setCustomerIdForBooking] = useState(null);
    const [customers, setCustomers] = useState([]);
    const [loadingCustomers, setLoadingCustomers] = useState(false);
    const [customerLoadingError, setCustomerLoadingError] = useState('');

    useEffect(() => {
        const loadCustomers = async () => {
            setLoadingCustomers(true);
            try {
                setCustomerLoadingError('');
                const fetchedCustomers = await fetchCustomers();
                setCustomers(fetchedCustomers || []);
            } catch (error) {
                console.error('Failed to load customers for dropdown:', error);
                setCustomerLoadingError('Could not load customers for selection.');
                setCustomers([]);
            } finally {
                setLoadingCustomers(false);
            }
        };
        loadCustomers();
    }, []);

    if (!seats || seats.length === 0) {
        return <p>No seat information available for this flight.</p>;
    }

    const seatsPerRow = 6;
    const rows = [];
    let currentRow = [];
    seats.forEach((seat, index) => {
        currentRow.push(seat);
        if ((index + 1) % seatsPerRow === 0 || index === seats.length - 1) {
            rows.push(currentRow);
            currentRow = [];
        }
    });

    const handleSeatClick = (seat) => {
        if (seat.isBooked) {
            let statusMsg = `Seat ${seat.seatId}: This seat is already booked.`;
            if (seat.bookedByCustomerId) {
                statusMsg = `Seat ${seat.seatId}: Booked by Customer ID ${seat.bookedByCustomerId}.`;
            }
            setBookingStatus(statusMsg);
            setSelectedSeatId(null);
            return;
        }
        setSelectedSeatId(seat.seatId);
        setBookingStatus(`Selected seat: ${seat.seatId} (${seat.seatClass}, Price: $${seat.price})`);
    };

    const handleCancelBookingFromSeat = async (bookingIdToCancel) => {
        if (!globalThis.confirm(`Are you sure you want to cancel booking ${bookingIdToCancel} for this seat?`)) {
            return;
        }
        setBookingStatus(`Cancelling booking ${bookingIdToCancel}...`);
        try {
            const result = await apiCancelBooking(bookingIdToCancel);
            setBookingStatus(result.message || `Booking ${bookingIdToCancel} cancellation processed.`);
            if (onBookingSuccess) {
                onBookingSuccess(flightNumber);
            }
        } catch (err) {
            setBookingStatus(`Failed to cancel booking ${bookingIdToCancel}: ${err.message}`);
            console.error('Cancellation error from seat map:', err);
        }
    };

    const handleConfirmBooking = async () => {
        if (seatMapInternals.applyBookingValidationError(selectedSeatId, customerIdForBooking, setBookingStatus)) {
            return;
        }

        const bookingData = {
            customerId: customerIdForBooking.value,
            flightNumber,
            seatId: selectedSeatId,
        };
        try {
            setBookingStatus('Processing booking...');
            const result = await createBooking(bookingData);
            setBookingStatus(`Booking successful! ID: ${result.bookingId}. Seat: ${result.seatId} for Customer: ${result.customerId}`);
            setSelectedSeatId(null);
            setCustomerIdForBooking(null);

            if (onBookingSuccess) {
                onBookingSuccess(flightNumber);
            }
        } catch (error) {
            setBookingStatus(`Booking failed: ${error.message}`);
            console.error('Booking error:', error);
        }
    };

    const getSeatStyle = (seat) => {
        const backgroundColor = seatMapInternals.resolveSeatBackgroundColor(seat, selectedSeatId);

        return {
            width: '60px',
            height: '60px',
            margin: '5px',
            border: '1px solid #ccc',
            backgroundColor,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.8em',
            position: 'relative',
        };
    };

    const getSeatButtonStyle = (seat) => ({
        border: 'none',
        background: 'transparent',
        font: 'inherit',
        padding: 0,
        margin: 0,
        cursor: seat.isBooked ? 'default' : 'pointer',
        color: 'inherit',
    });

    return (
        <div>
            <h4>Seat Map for {flightNumber}</h4>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                {rows.map((row) => (
                    <div key={row[0].seatId} style={{ display: 'flex' }}>
                        {row.map((seat) => (
                            <div key={seat.seatId} style={getSeatStyle(seat)}>
                                <button
                                    type="button"
                                    onClick={() => handleSeatClick(seat)}
                                    style={getSeatButtonStyle(seat)}
                                    aria-label={`Seat ${seat.seatId}`}
                                    aria-pressed={selectedSeatId === seat.seatId}
                                >
                                    {seat.seatId}
                                </button>
                                {seat.isBooked && seat.bookingId && (
                                    <button
                                        type="button"
                                        onClick={() => handleCancelBookingFromSeat(seat.bookingId)}
                                        style={{ fontSize: '0.6em', padding: '1px 3px', marginTop: '3px', cursor: 'pointer' }}
                                        aria-label={`Cancel booking ${seat.bookingId}`}
                                        title={`Cancel booking ${seat.bookingId}`}
                                    >
                                        Cancel
                                    </button>
                                )}
                            </div>
                        ))}
                    </div>
                ))}
            </div>
            {bookingStatus && <p aria-live="polite">{bookingStatus}</p>}
            {customerLoadingError && <p aria-live="polite" style={{ color: 'red' }}>{customerLoadingError}</p>}
            {selectedSeatId && (
                <div style={{ marginTop: '10px' }}>
                    <label htmlFor="customerSelectBooking" style={{ marginRight: '10px' }}>Select Customer:</label>
                    {loadingCustomers ? (
                        <span>Loading customers...</span>
                    ) : (
                        <Select
                            inputId="customerSelectBooking"
                            value={customerIdForBooking}
                            onChange={setCustomerIdForBooking}
                            options={customers.map((cust) => ({ value: cust.personId, label: `${cust.name} (ID: ${cust.personId})` }))}
                            isClearable
                            isSearchable
                            placeholder="Select or type to search Customer..."
                            isDisabled={customers.length === 0 && !customerLoadingError}
                            styles={{ container: (base) => ({ ...base, width: '300px', marginRight: '10px', display: 'inline-block' }) }}
                        />
                    )}
                    <button
                        type="button"
                        onClick={handleConfirmBooking}
                        disabled={!customerIdForBooking?.value || loadingCustomers}
                    >
                        Confirm Booking for {selectedSeatId}
                    </button>
                </div>
            )}
            <div style={{ marginTop: '10px' }}>
                <span style={{ marginRight: '5px' }}>Legend:</span>
                <span style={{ backgroundColor: 'lightgreen', padding: '2px 5px', margin: '0 5px' }}>Available Economy</span>
                <span style={{ backgroundColor: 'lightblue', padding: '2px 5px', margin: '0 5px' }}>Available Business</span>
                <span style={{ backgroundColor: 'lightcoral', padding: '2px 5px', margin: '0 5px' }}>Booked</span>
                <span style={{ backgroundColor: 'yellow', padding: '2px 5px', margin: '0 5px' }}>Selected</span>
            </div>
        </div>
    );
};

SeatMap.propTypes = {
    seats: PropTypes.arrayOf(PropTypes.shape({
        seatId: PropTypes.string.isRequired,
        seatClass: PropTypes.string.isRequired,
        price: PropTypes.number.isRequired,
        isBooked: PropTypes.bool.isRequired,
        bookedByCustomerId: PropTypes.string,
        bookingId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    })).isRequired,
    flightNumber: PropTypes.string.isRequired,
    onBookingSuccess: PropTypes.func,
};

export default SeatMap;
export const __internal = seatMapInternals;
