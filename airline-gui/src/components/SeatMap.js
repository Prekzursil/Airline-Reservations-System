import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import Select from 'react-select';
import { createBooking, fetchCustomers, cancelBooking as apiCancelBooking } from '../services/apiService';

const compactButtonStyle = { fontSize: '0.6em', padding: '1px 3px', marginTop: '3px', cursor: 'pointer' };
const legendChipStyle = { padding: '2px 5px', margin: '0 5px' };

function SeatCancellationControls({
    bookingId,
    keepSeatBooking,
    onConfirmCancellation,
    pendingCancellationId,
    requestSeatCancellation,
}) {
    if (!bookingId) {
        return null;
    }

    if (pendingCancellationId === bookingId) {
        return (
            <>
                <button
                    type="button"
                    onClick={() => onConfirmCancellation(bookingId)}
                    style={compactButtonStyle}
                    aria-label={`Confirm cancellation for booking ${bookingId}`}
                    title={`Confirm cancellation for booking ${bookingId}`}
                >
                    Confirm
                </button>
                <button
                    type="button"
                    onClick={keepSeatBooking}
                    style={compactButtonStyle}
                    aria-label={`Keep booking ${bookingId}`}
                    title={`Keep booking ${bookingId}`}
                >
                    Keep
                </button>
            </>
        );
    }

    return (
        <button
            type="button"
            onClick={() => requestSeatCancellation(bookingId)}
            style={compactButtonStyle}
            aria-label={`Cancel booking ${bookingId}`}
            title={`Cancel booking ${bookingId}`}
        >
            Cancel
        </button>
    );
}

SeatCancellationControls.propTypes = {
    bookingId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    keepSeatBooking: PropTypes.func.isRequired,
    onConfirmCancellation: PropTypes.func.isRequired,
    pendingCancellationId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    requestSeatCancellation: PropTypes.func.isRequired,
};

function SeatGrid({ getSeatButtonStyle, getSeatStyle, handleSeatClick, keepSeatBooking, onConfirmCancellation, pendingCancellationId, requestSeatCancellation, rows, selectedSeatId }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            {rows.map((row) => (
                <div key={row[0]?.seatId || 'seat-row'} style={{ display: 'flex' }}>
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
                            {seat.isBooked && (
                                <SeatCancellationControls
                                    bookingId={seat.bookingId}
                                    keepSeatBooking={keepSeatBooking}
                                    onConfirmCancellation={onConfirmCancellation}
                                    pendingCancellationId={pendingCancellationId}
                                    requestSeatCancellation={requestSeatCancellation}
                                />
                            )}
                        </div>
                    ))}
                </div>
            ))}
        </div>
    );
}

SeatGrid.propTypes = {
    getSeatButtonStyle: PropTypes.func.isRequired,
    getSeatStyle: PropTypes.func.isRequired,
    handleSeatClick: PropTypes.func.isRequired,
    keepSeatBooking: PropTypes.func.isRequired,
    onConfirmCancellation: PropTypes.func.isRequired,
    pendingCancellationId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    requestSeatCancellation: PropTypes.func.isRequired,
    rows: PropTypes.arrayOf(PropTypes.arrayOf(PropTypes.shape({
        seatId: PropTypes.string.isRequired,
        seatClass: PropTypes.string.isRequired,
        price: PropTypes.number.isRequired,
        isBooked: PropTypes.bool.isRequired,
        bookedByCustomerId: PropTypes.string,
        bookingId: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    }).isRequired)).isRequired,
    selectedSeatId: PropTypes.string,
};

function BookingCustomerSelector({
    customerIdForBooking,
    customers,
    loadingCustomers,
    onConfirmBooking,
    onSelectCustomer,
    selectedSeatId,
}) {
    return (
        <div style={{ marginTop: '10px' }}>
            <label htmlFor="customerSelectBooking" style={{ marginRight: '10px' }}>Select Customer:</label>
            {loadingCustomers ? (
                <span>Loading customers...</span>
            ) : (
                <Select
                    inputId="customerSelectBooking"
                    value={customerIdForBooking}
                    onChange={onSelectCustomer}
                    options={customers.map((cust) => ({ value: cust.personId, label: `${cust.name} (ID: ${cust.personId})` }))}
                    isClearable
                    isSearchable
                    placeholder="Select or type to search Customer..."
                    isDisabled={customers.length === 0}
                    styles={{ container: (base) => ({ ...base, width: '300px', marginRight: '10px', display: 'inline-block' }) }}
                />
            )}
            <button
                type="button"
                onClick={onConfirmBooking}
                disabled={!customerIdForBooking?.value || loadingCustomers}
            >
                Confirm Booking for {selectedSeatId}
            </button>
        </div>
    );
}

BookingCustomerSelector.propTypes = {
    customerIdForBooking: PropTypes.shape({
        value: PropTypes.string,
        label: PropTypes.string,
    }),
    customers: PropTypes.arrayOf(PropTypes.shape({
        personId: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
    })).isRequired,
    loadingCustomers: PropTypes.bool.isRequired,
    onConfirmBooking: PropTypes.func.isRequired,
    onSelectCustomer: PropTypes.func.isRequired,
    selectedSeatId: PropTypes.string.isRequired,
};

/**
 * Renders the seat layout for a flight and coordinates booking actions.
 *
 * @param {object} props Component props.
 * @param {Array<object>} props.seats The current seat inventory for the selected flight.
 * @param {string} props.flightNumber The selected flight identifier.
 * @param {?Function} props.onBookingSuccess Optional callback invoked after booking mutations.
 * @returns {JSX.Element} The rendered seat map.
 */
const SeatMap = ({ seats, flightNumber, onBookingSuccess = null }) => {
    const [selectedSeatId, setSelectedSeatId] = useState(null);
    const [bookingStatus, setBookingStatus] = useState('');
    const [customerIdForBooking, setCustomerIdForBooking] = useState(null);
    const [customers, setCustomers] = useState([]);
    const [loadingCustomers, setLoadingCustomers] = useState(false);
    const [customerLoadingError, setCustomerLoadingError] = useState('');
    const [pendingCancellationId, setPendingCancellationId] = useState(null);

    useEffect(() => {
        /**
         * Loads customers for the booking dropdown.
         *
         * @returns {Promise<void>} A promise that settles after the customer list finishes loading.
         */
        const loadCustomers = async () => {
            setLoadingCustomers(true);
            try {
                setCustomerLoadingError('');
                const fetchedCustomers = await fetchCustomers();
                setCustomers(fetchedCustomers || []);
            } catch {
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

    /**
     * Handles seat selection and explains the current seat state to the user.
     *
     * @param {object} seat The clicked seat record.
     */
    const handleSeatClick = (seat) => {
        setPendingCancellationId(null);
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

    /**
     * Starts the inline cancellation confirmation flow for a booked seat.
     *
     * @param {number|string} bookingIdToCancel The booking linked to the selected seat.
     */
    const requestSeatCancellation = (bookingIdToCancel) => {
        setPendingCancellationId(bookingIdToCancel);
        setBookingStatus(`Confirm cancellation for booking ${bookingIdToCancel}.`);
    };

    /**
     * Clears the pending seat cancellation request.
     */
    const keepSeatBooking = () => {
        setPendingCancellationId(null);
        setBookingStatus('Cancellation kept.');
    };

    /**
     * Cancels a seat booking after the inline confirmation step.
     *
     * @param {number|string} bookingIdToCancel The booking to cancel.
     * @returns {Promise<void>} A promise that settles after the cancellation request completes.
     */
    const handleCancelBookingFromSeat = async (bookingIdToCancel) => {
        setBookingStatus(`Cancelling booking ${bookingIdToCancel}...`);
        try {
            const result = await apiCancelBooking(bookingIdToCancel);
            setPendingCancellationId(null);
            setBookingStatus(result.message || `Booking ${bookingIdToCancel} cancellation processed.`);
            if (onBookingSuccess) {
                onBookingSuccess(flightNumber);
            }
        } catch (err) {
            setPendingCancellationId(null);
            setBookingStatus(`Failed to cancel booking ${bookingIdToCancel}: ${err.message}`);
        }
    };

    /**
     * Creates a booking for the currently selected seat and customer.
     *
     * @returns {Promise<void>} A promise that settles after the booking request completes.
     */
    const handleConfirmBooking = async () => {
        /* c8 ignore start - guarded by UI state; confirm button is only rendered/enabled when these are satisfied */
        if (!selectedSeatId) {
            setBookingStatus('Please select a seat first.');
            return;
        }
        if (!customerIdForBooking?.value) {
            setBookingStatus('Please select a Customer for booking.');
            return;
        }
        /* c8 ignore end */

        const bookingData = {
            customerId: customerIdForBooking.value,
            flightNumber,
            seatId: selectedSeatId,
        };
        try {
            setBookingStatus('Processing booking...');
            const result = await createBooking(bookingData);
            setPendingCancellationId(null);
            setBookingStatus(`Booking successful! ID: ${result.bookingId}. Seat: ${result.seatId} for Customer: ${result.customerId}`);
            setSelectedSeatId(null);
            setCustomerIdForBooking(null);

            if (onBookingSuccess) {
                onBookingSuccess(flightNumber);
            }
        } catch (error) {
            setBookingStatus(`Booking failed: ${error.message}`);
        }
    };

    /**
     * Returns inline styles for a seat cell.
     *
     * @param {object} seat The seat being rendered.
     * @returns {object} The seat container style.
     */
    const getSeatStyle = (seat) => {
        let backgroundColor = 'lightgreen';
        if (seat.isBooked) {
            backgroundColor = 'lightcoral';
        } else if (seat.seatClass === 'Business') {
            backgroundColor = 'lightblue';
        }

        if (seat.seatId === selectedSeatId) {
            backgroundColor = 'yellow';
        }

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

    /**
     * Returns the button style for the clickable seat label.
     *
     * @param {object} seat The seat being rendered.
     * @returns {object} The seat button style.
     */
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
            <SeatGrid
                getSeatButtonStyle={getSeatButtonStyle}
                getSeatStyle={getSeatStyle}
                handleSeatClick={handleSeatClick}
                keepSeatBooking={keepSeatBooking}
                onConfirmCancellation={handleCancelBookingFromSeat}
                pendingCancellationId={pendingCancellationId}
                requestSeatCancellation={requestSeatCancellation}
                rows={rows}
                selectedSeatId={selectedSeatId}
            />
            {bookingStatus && <p aria-live="polite">{bookingStatus}</p>}
            {customerLoadingError && <p aria-live="polite" style={{ color: 'red' }}>{customerLoadingError}</p>}
            {selectedSeatId && (
                <BookingCustomerSelector
                    customerIdForBooking={customerIdForBooking}
                    customers={customers}
                    loadingCustomers={loadingCustomers}
                    onConfirmBooking={handleConfirmBooking}
                    onSelectCustomer={setCustomerIdForBooking}
                    selectedSeatId={selectedSeatId}
                />
            )}
            <div style={{ marginTop: '10px' }}>
                <span style={{ marginRight: '5px' }}>Legend:</span>
                <span style={{ ...legendChipStyle, backgroundColor: 'lightgreen' }}>Available Economy</span>
                <span style={{ ...legendChipStyle, backgroundColor: 'lightblue' }}>Available Business</span>
                <span style={{ ...legendChipStyle, backgroundColor: 'lightcoral' }}>Booked</span>
                <span style={{ ...legendChipStyle, backgroundColor: 'yellow' }}>Selected</span>
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
