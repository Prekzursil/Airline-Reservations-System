import { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import Select from 'react-select';
import { swapSeats, fetchBookings } from '../services/apiService';

// Shared prop-type fragments for the booking selector inputs. Defining the
// option and selected-value shapes once keeps BookingSelectField and
// SwapBookingField in sync without duplicating the nested PropTypes.shape calls.
const bookingOptionShape = PropTypes.shape({
    value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]).isRequired,
    label: PropTypes.string.isRequired,
});
const bookingValueShape = PropTypes.shape({
    value: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    label: PropTypes.string,
});
const sharedSelectorPropTypes = {
    disabled: PropTypes.bool.isRequired,
    inputId: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
    options: PropTypes.arrayOf(bookingOptionShape.isRequired).isRequired,
    placeholder: PropTypes.string.isRequired,
    value: bookingValueShape,
};

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

BookingSelectField.propTypes = { ...sharedSelectorPropTypes };

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
    ...sharedSelectorPropTypes,
    label: PropTypes.string.isRequired,
};

/**
 * Builds the confirmed-booking options shown in the swap selectors.
 *
 * @param {Array<object>} bookings All bookings returned by the API.
 * @returns {Array<{value: (number|string), label: string}>} Selector options.
 */
const buildBookingOptions = (bookings) => bookings
    .filter((booking) => booking.status === 'Confirmed')
    .map((booking) => ({
        value: booking.bookingId,
        label: `ID: ${booking.bookingId} (Cust: ${booking.customerId}, Flight: ${booking.flightNumber}, Seat: ${booking.seatId})`,
    }));

/**
 * Validates a pair of selected bookings before requesting a swap.
 *
 * @param {?object} booking1 The first selected booking option.
 * @param {?object} booking2 The second selected booking option.
 * @returns {string} A validation message, or an empty string when valid.
 */
const validateSwapSelection = (booking1, booking2) => {
    if (!booking1?.value || !booking2?.value) {
        return 'Please select both bookings.';
    }
    if (booking1.value === booking2.value) {
        return 'Booking IDs must be different.';
    }
    return '';
};

/**
 * Returns the options for one selector, excluding the other booking's value.
 *
 * @param {Array<object>} options All confirmed-booking options.
 * @param {?object} otherBooking The booking chosen in the sibling selector.
 * @returns {Array<object>} Options without the sibling selection.
 */
const optionsExcluding = (options, otherBooking) =>
    options.filter((opt) => opt.value !== otherBooking?.value);

/**
 * Computes the swap form's derived display state from its inputs.
 *
 * @param {object} state Current form state flags and selections.
 * @returns {{formIsDisabled: boolean, showEmptyState: boolean, submitDisabled: boolean}}
 *   Flags controlling the form's enabled/empty/submit presentation.
 */
const deriveFormState = ({
    loadingBookings,
    errorLoadingBookings,
    bookingsCount,
    optionsCount,
    booking1,
    booking2,
}) => ({
    formIsDisabled: loadingBookings || optionsCount === 0,
    showEmptyState: !loadingBookings && !errorLoadingBookings && bookingsCount === 0,
    submitDisabled: loadingBookings || !booking1 || !booking2,
});

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

    const bookingOptions = buildBookingOptions(allBookings);

    /**
     * Submits the seat swap request for the selected bookings.
     *
     * @param {Event} event The form submission event.
     * @returns {Promise<void>} A promise that settles after the swap request completes.
     */
    const handleSubmit = async (event) => {
        event.preventDefault();
        const message = validateSwapSelection(selectedBooking1, selectedBooking2);
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

    const { formIsDisabled, showEmptyState, submitDisabled } = deriveFormState({
        loadingBookings,
        errorLoadingBookings,
        bookingsCount: allBookings.length,
        optionsCount: bookingOptions.length,
        booking1: selectedBooking1,
        booking2: selectedBooking2,
    });

    return (
        <div>
            <h3>Swap Seats Between Two Bookings</h3>
            {loadingBookings && <p aria-live="polite">Loading bookings...</p>}
            {errorLoadingBookings && <p aria-live="polite" style={{ color: 'red' }}>{errorLoadingBookings}</p>}
            {showEmptyState && <p>No confirmed bookings available to swap.</p>}

            <form onSubmit={handleSubmit} style={{ opacity: formIsDisabled ? 0.5 : 1 }}>
                <SwapBookingField
                    disabled={formIsDisabled}
                    inputId="booking1SelectSwap"
                    label="Select First Booking:"
                    onChange={setSelectedBooking1}
                    options={optionsExcluding(bookingOptions, selectedBooking2)}
                    placeholder="Select Booking 1..."
                    value={selectedBooking1}
                />
                <SwapBookingField
                    disabled={formIsDisabled}
                    inputId="booking2SelectSwap"
                    label="Select Second Booking:"
                    onChange={setSelectedBooking2}
                    options={optionsExcluding(bookingOptions, selectedBooking1)}
                    placeholder="Select Booking 2..."
                    value={selectedBooking2}
                />
                <button type="submit" style={{ marginTop: '10px' }} disabled={submitDisabled}>
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
