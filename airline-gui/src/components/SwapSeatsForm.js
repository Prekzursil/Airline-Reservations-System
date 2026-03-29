import { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import Select from 'react-select';
import { swapSeats, fetchBookings } from '../services/apiService';

/**
 * Renders a booking selector field.
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} The rendered selector field.
 */
function BookingSelectField({ disabled, inputId, onChange, options, placeholder, value }) {
    return (
        <Select
            inputId={inputId}
            value={value}
            onChange={onChange}
            options={options}
            isClearable
            isSearchable
            placeholder={placeholder}
            isDisabled={disabled}
        />
    );
}

BookingSelectField.propTypes = {
    disabled: PropTypes.bool.isRequired,
    inputId: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
    options: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
        label: PropTypes.string.isRequired,
    }).isRequired).isRequired,
    placeholder: PropTypes.string.isRequired,
    value: PropTypes.shape({
        value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
        label: PropTypes.string,
    }),
};

/**
 * Renders one labeled booking selector row in the swap form.
 *
 * @param {object} props Component props.
 * @returns {JSX.Element} The rendered booking selector row.
 */
function SwapBookingField({ disabled, inputId, label, onChange, options, placeholder, value }) {
    return (
        <div style={{ marginBottom: '10px' }}>
            <label htmlFor={inputId} style={{ display: 'block', marginBottom: '4px' }}>{label}</label>
            <BookingSelectField
                disabled={disabled}
                inputId={inputId}
                onChange={onChange}
                options={options}
                placeholder={placeholder}
                value={value}
            />
        </div>
    );
}

SwapBookingField.propTypes = {
    disabled: PropTypes.bool.isRequired,
    inputId: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
    options: PropTypes.arrayOf(PropTypes.shape({
        value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
        label: PropTypes.string.isRequired,
    }).isRequired).isRequired,
    placeholder: PropTypes.string.isRequired,
    value: PropTypes.shape({
        value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
        label: PropTypes.string,
    }),
};

/**
 * Renders the seat-swap form for two confirmed bookings.
 *
 * @param {object} props Component props.
 * @param {?Function} props.onSeatsSwapped Optional callback invoked after a successful seat swap.
 * @param {number|string} props.refreshTrigger Token used to reload the booking options.
 * @returns {JSX.Element} The rendered swap form.
 */
const SwapSeatsForm = ({ onSeatsSwapped = null, refreshTrigger }) => {
    const [allBookings, setAllBookings] = useState([]);
    const [selectedBooking1, setSelectedBooking1] = useState(null);
    const [selectedBooking2, setSelectedBooking2] = useState(null);
    const [statusMessage, setStatusMessage] = useState('');
    const [loadingBookings, setLoadingBookings] = useState(false);
    const [errorLoadingBookings, setErrorLoadingBookings] = useState('');

    useEffect(() => {
        /**
         * Loads the booking options used by the swap form.
         *
         * @returns {Promise<void>} A promise that settles after bookings are loaded.
         */
        const loadBookings = async () => {
            setLoadingBookings(true);
            setErrorLoadingBookings('');
            try {
                const bookingsData = await fetchBookings();
                setAllBookings(bookingsData || []);
            } catch {
                setErrorLoadingBookings('Could not load bookings.');
                setAllBookings([]);
            } finally {
                setLoadingBookings(false);
            }
        };
        loadBookings();
    }, [refreshTrigger]);

    const bookingOptions = allBookings
        .filter((booking) => booking.status === 'Confirmed')
        .map((booking) => ({
            value: booking.bookingId,
            label: `ID: ${booking.bookingId} (Cust: ${booking.customerId}, Flight: ${booking.flightNumber}, Seat: ${booking.seatId})`,
        }));

    /**
     * Validates the current booking selections before submitting the swap request.
     *
     * @returns {string} A validation message when the form is incomplete, otherwise an empty string.
     */
    const validationMessage = () => {
        if (!selectedBooking1?.value || !selectedBooking2?.value) {
            return 'Please select both bookings.';
        }
        if (selectedBooking1.value === selectedBooking2.value) {
            return 'Booking IDs must be different.';
        }
        return '';
    };

    /**
     * Submits the seat swap request for the selected bookings.
     *
     * @param {Event} event The form submission event.
     * @returns {Promise<void>} A promise that settles after the swap request completes.
     */
    const handleSubmit = async (event) => {
        event.preventDefault();
        const message = validationMessage();
        if (message) {
            setStatusMessage(message);
            return;
        }
        setStatusMessage('Processing seat swap...');
        try {
            const result = await swapSeats(selectedBooking1.value, selectedBooking2.value);
            setStatusMessage(result.message || 'Seat swap processed.');
            setSelectedBooking1(null);
            setSelectedBooking2(null);
            if (onSeatsSwapped) {
                onSeatsSwapped();
            }
        } catch (error) {
            setStatusMessage(`Failed to swap seats: ${error.message}`);
        }
    };

    const formIsDisabled = loadingBookings || bookingOptions.length === 0;
    const emptyStateMessage = !loadingBookings && !errorLoadingBookings && allBookings.length === 0
        ? <p>No confirmed bookings available to swap.</p>
        : null;

    return (
        <div>
            <h3>Swap Seats Between Two Bookings</h3>
            {loadingBookings && <p aria-live="polite">Loading bookings...</p>}
            {errorLoadingBookings && <p aria-live="polite" style={{ color: 'red' }}>{errorLoadingBookings}</p>}
            {emptyStateMessage}

            <form onSubmit={handleSubmit} style={{ opacity: formIsDisabled ? 0.5 : 1 }}>
                <SwapBookingField
                    disabled={formIsDisabled}
                    inputId="booking1SelectSwap"
                    label="Select First Booking:"
                    onChange={setSelectedBooking1}
                    options={bookingOptions.filter((opt) => opt.value !== selectedBooking2?.value)}
                    placeholder="Select Booking 1..."
                    value={selectedBooking1}
                />
                <SwapBookingField
                    disabled={formIsDisabled}
                    inputId="booking2SelectSwap"
                    label="Select Second Booking:"
                    onChange={setSelectedBooking2}
                    options={bookingOptions.filter((opt) => opt.value !== selectedBooking1?.value)}
                    placeholder="Select Booking 2..."
                    value={selectedBooking2}
                />
                <button type="submit" style={{ marginTop: '10px' }} disabled={loadingBookings || !selectedBooking1 || !selectedBooking2}>
                    Swap Selected Seats
                </button>
            </form>
            {statusMessage && <p aria-live="polite">{statusMessage}</p>}
        </div>
    );
};

SwapSeatsForm.propTypes = {
    onSeatsSwapped: PropTypes.func,
    refreshTrigger: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
};

export default SwapSeatsForm;
