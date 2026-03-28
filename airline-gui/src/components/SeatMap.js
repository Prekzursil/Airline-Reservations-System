import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import Select from 'react-select';
import { createBooking, fetchCustomers, cancelBooking as apiCancelBooking } from '../services/apiService';

const SEAT_BUTTON_STYLE = {
    border: 'none',
    background: 'transparent',
    font: 'inherit',
    padding: 0,
    margin: 0,
    color: 'inherit',
};

const buildSeatRows = (seats, seatsPerRow) => {
    const rows = [];
    let currentRow = [];
    seats.forEach((seat, index) => {
        currentRow.push(seat);
        if ((index + 1) % seatsPerRow === 0 || index === seats.length - 1) {
            rows.push(currentRow);
            currentRow = [];
        }
    });
    return rows;
};

const seatBackgroundColor = (seat, selectedSeatId) => {
    if (seat.seatId === selectedSeatId) {
        return 'yellow';
    }
    if (seat.isBooked) {
        return 'lightcoral';
    }
    if (seat.seatClass === 'Business') {
        return 'lightblue';
    }
    return 'lightgreen';
};

const getSeatStyle = (seat, selectedSeatId) => ({
    width: '60px',
    height: '60px',
    margin: '5px',
    border: '1px solid #ccc',
    backgroundColor: seatBackgroundColor(seat, selectedSeatId),
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.8em',
    position: 'relative',
});

const getSeatButtonStyle = (seat) => ({
    ...SEAT_BUTTON_STYLE,
    cursor: seat.isBooked ? 'default' : 'pointer',
});

const customerOptions = (customers) => customers.map((cust) => ({
    value: cust.personId,
    label: `${cust.name} (ID: ${cust.personId})`,
}));

const CANCEL_BUTTON_STYLE = {
    fontSize: '0.6em',
    padding: '1px 3px',
    marginTop: '3px',
    cursor: 'pointer',
};

const SELECT_CONTAINER_STYLE = {
    width: '300px',
    marginRight: '10px',
    display: 'inline-block',
};

const LEGEND_ITEMS = [
    { label: 'Available Economy', color: 'lightgreen' },
    { label: 'Available Business', color: 'lightblue' },
    { label: 'Booked', color: 'lightcoral' },
    { label: 'Selected', color: 'yellow' },
];

const bookingIdPropType = PropTypes.oneOfType([PropTypes.number, PropTypes.string]);
const seatPropType = PropTypes.shape({
    seatId: PropTypes.string.isRequired,
    seatClass: PropTypes.string.isRequired,
    price: PropTypes.number.isRequired,
    isBooked: PropTypes.bool.isRequired,
    bookedByCustomerId: PropTypes.string,
    bookingId: bookingIdPropType,
}).isRequired;
const customerPropType = PropTypes.shape({
    personId: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
}).isRequired;
const customerSelectionPropType = PropTypes.shape({
    value: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
});
const seatRowPropType = PropTypes.arrayOf(seatPropType).isRequired;

const selectionStatusForSeat = (seat) => {
    if (!seat.isBooked) {
        return {
            selectedSeatId: seat.seatId,
            status: `Selected seat: ${seat.seatId} (${seat.seatClass}, Price: $${seat.price})`,
        };
    }

    const bookedByCustomerId = seat.bookedByCustomerId
        ? `Booked by Customer ID ${seat.bookedByCustomerId}.`
        : 'This seat is already booked.';
    return {
        selectedSeatId: null,
        status: `Seat ${seat.seatId}: ${bookedByCustomerId}`,
    };
};

const useCustomers = () => {
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

    return {
        customers,
        loadingCustomers,
        customerLoadingError,
    };
};

const bookingRequestForSelection = (selectedSeatId, customerIdForBooking, flightNumber) => {
    if (!selectedSeatId) {
        return { status: 'Please select a seat first.' };
    }
    if (!customerIdForBooking?.value) {
        return { status: 'Please select a Customer for booking.' };
    }
    return {
        bookingData: {
            customerId: customerIdForBooking.value,
            flightNumber,
            seatId: selectedSeatId,
        },
    };
};

const performBooking = async (bookingData) => createBooking(bookingData);

const SeatCell = ({ seat, isSelected, onSeatClick, onCancelBooking }) => (
    <div style={getSeatStyle(seat, isSelected ? seat.seatId : null)}>
        <button
            type="button"
            onClick={() => onSeatClick(seat)}
            style={getSeatButtonStyle(seat)}
            aria-label={`Seat ${seat.seatId}`}
            aria-pressed={isSelected}
        >
            {seat.seatId}
        </button>
        {seat.isBooked && seat.bookingId && (
            <button
                type="button"
                onClick={() => onCancelBooking(seat.bookingId)}
                style={CANCEL_BUTTON_STYLE}
                aria-label={`Cancel booking ${seat.bookingId}`}
                title={`Cancel booking ${seat.bookingId}`}
            >
                Cancel
            </button>
        )}
    </div>
);

SeatCell.propTypes = {
    seat: seatPropType,
    isSelected: PropTypes.bool.isRequired,
    onSeatClick: PropTypes.func.isRequired,
    onCancelBooking: PropTypes.func.isRequired,
};

const SeatGrid = ({ rows, selectedSeatId, onSeatClick, onCancelBooking }) => (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {rows.map((row) => (
            <div key={row[0]?.seatId || 'seat-row'} style={{ display: 'flex' }}>
                {row.map((seat) => (
                    <SeatCell
                        key={seat.seatId}
                        seat={seat}
                        isSelected={selectedSeatId === seat.seatId}
                        onSeatClick={onSeatClick}
                        onCancelBooking={onCancelBooking}
                    />
                ))}
            </div>
        ))}
    </div>
);

SeatGrid.propTypes = {
    rows: PropTypes.arrayOf(seatRowPropType).isRequired,
    selectedSeatId: PropTypes.string,
    onSeatClick: PropTypes.func.isRequired,
    onCancelBooking: PropTypes.func.isRequired,
};

const BookingControls = ({
    selectedSeatId,
    loadingCustomers,
    customerLoadingError,
    customers,
    customerIdForBooking,
    onCustomerChange,
    onConfirmBooking,
}) => {
    if (!selectedSeatId) {
        return null;
    }

    return (
        <div style={{ marginTop: '10px' }}>
            <label htmlFor="customerSelectBooking" style={{ marginRight: '10px' }}>Select Customer:</label>
            {loadingCustomers ? (
                <span>Loading customers...</span>
            ) : (
                <Select
                    inputId="customerSelectBooking"
                    value={customerIdForBooking}
                    onChange={onCustomerChange}
                    options={customerOptions(customers)}
                    isClearable
                    isSearchable
                    placeholder="Select or type to search Customer..."
                    isDisabled={customers.length === 0 && !customerLoadingError}
                    styles={{ container: (base) => ({ ...base, ...SELECT_CONTAINER_STYLE }) }}
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
};

BookingControls.propTypes = {
    selectedSeatId: PropTypes.string,
    loadingCustomers: PropTypes.bool.isRequired,
    customerLoadingError: PropTypes.string.isRequired,
    customers: PropTypes.arrayOf(customerPropType).isRequired,
    customerIdForBooking: customerSelectionPropType,
    onCustomerChange: PropTypes.func.isRequired,
    onConfirmBooking: PropTypes.func.isRequired,
};

const Legend = () => (
    <div style={{ marginTop: '10px' }}>
        <span style={{ marginRight: '5px' }}>Legend:</span>
        {LEGEND_ITEMS.map((item) => (
            <span
                key={item.label}
                style={{ backgroundColor: item.color, padding: '2px 5px', margin: '0 5px' }}
            >
                {item.label}
            </span>
        ))}
    </div>
);

const SeatMapContent = ({
    hasSeats,
    rows,
    selectedSeatId,
    loadingCustomers,
    customerLoadingError,
    customers,
    customerIdForBooking,
    onSeatClick,
    onCancelBooking,
    onCustomerChange,
    onConfirmBooking,
}) => {
    if (!hasSeats) {
        return <p>No seat information available for this flight.</p>;
    }

    return (
        <>
            <SeatGrid
                rows={rows}
                selectedSeatId={selectedSeatId}
                onSeatClick={onSeatClick}
                onCancelBooking={onCancelBooking}
            />
            <BookingControls
                selectedSeatId={selectedSeatId}
                loadingCustomers={loadingCustomers}
                customerLoadingError={customerLoadingError}
                customers={customers}
                customerIdForBooking={customerIdForBooking}
                onCustomerChange={onCustomerChange}
                onConfirmBooking={onConfirmBooking}
            />
        </>
    );
};

SeatMapContent.propTypes = {
    hasSeats: PropTypes.bool.isRequired,
    rows: PropTypes.arrayOf(seatRowPropType).isRequired,
    selectedSeatId: PropTypes.string,
    loadingCustomers: PropTypes.bool.isRequired,
    customerLoadingError: PropTypes.string.isRequired,
    customers: PropTypes.arrayOf(customerPropType).isRequired,
    customerIdForBooking: customerSelectionPropType,
    onSeatClick: PropTypes.func.isRequired,
    onCancelBooking: PropTypes.func.isRequired,
    onCustomerChange: PropTypes.func.isRequired,
    onConfirmBooking: PropTypes.func.isRequired,
};

const SeatMap = ({ seats, flightNumber, onBookingSuccess = null }) => {
    const [selectedSeatId, setSelectedSeatId] = useState(null);
    const [bookingStatus, setBookingStatus] = useState('');
    const [customerIdForBooking, setCustomerIdForBooking] = useState(null);
    const { customers, loadingCustomers, customerLoadingError } = useCustomers();

    const seatsPerRow = 6;
    const hasSeats = Boolean(seats && seats.length > 0);
    const rows = hasSeats ? buildSeatRows(seats, seatsPerRow) : [];

    const handleSeatClick = (seat) => {
        const nextSelection = selectionStatusForSeat(seat);
        setSelectedSeatId(nextSelection.selectedSeatId);
        setBookingStatus(nextSelection.status);
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
        const bookingData = {
            customerId: customerIdForBooking.value,
            flightNumber,
            seatId: selectedSeatId,
        };

        try {
            setBookingStatus('Processing booking...');
            const result = await performBooking(bookingData);
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

    return (
        <div>
            <h4>Seat Map for {flightNumber}</h4>
            <SeatMapContent
                hasSeats={hasSeats}
                rows={rows}
                selectedSeatId={selectedSeatId}
                loadingCustomers={loadingCustomers}
                customerLoadingError={customerLoadingError}
                customers={customers}
                customerIdForBooking={customerIdForBooking}
                onSeatClick={handleSeatClick}
                onCancelBooking={handleCancelBookingFromSeat}
                onCustomerChange={setCustomerIdForBooking}
                onConfirmBooking={handleConfirmBooking}
            />
            {bookingStatus && <p aria-live="polite">{bookingStatus}</p>}
            {customerLoadingError && <p aria-live="polite" style={{ color: 'red' }}>{customerLoadingError}</p>}
            <Legend />
        </div>
    );
};

SeatMap.propTypes = {
    seats: PropTypes.arrayOf(seatPropType).isRequired,
    flightNumber: PropTypes.string.isRequired,
    onBookingSuccess: PropTypes.func,
};

export { bookingRequestForSelection, seatBackgroundColor, selectionStatusForSeat };
export default SeatMap;
