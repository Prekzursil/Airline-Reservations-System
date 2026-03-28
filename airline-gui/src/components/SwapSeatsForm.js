import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import Select from 'react-select';
import { swapSeats, fetchBookings } from '../services/apiService';

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
            } catch (error) {
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

    return (
        <div>
            <h3>Swap Seats Between Two Bookings</h3>
            {loadingBookings && <p aria-live="polite">Loading bookings...</p>}
            {errorLoadingBookings && <p aria-live="polite" style={{ color: 'red' }}>{errorLoadingBookings}</p>}
            {!loadingBookings && !errorLoadingBookings && allBookings.length === 0 && <p>No confirmed bookings available to swap.</p>}

            <form onSubmit={handleSubmit} style={{ opacity: loadingBookings || allBookings.length === 0 ? 0.5 : 1 }}>
                <div style={{ marginBottom: '10px' }}>
                    <label htmlFor="booking1SelectSwap" style={{ display: 'block', marginBottom: '4px' }}>Select First Booking:</label>
                    <Select
                        inputId="booking1SelectSwap"
                        value={selectedBooking1}
                        onChange={setSelectedBooking1}
                        options={bookingOptions.filter((opt) => opt.value !== selectedBooking2?.value)}
                        isClearable
                        isSearchable
                        placeholder="Select Booking 1..."
                        isDisabled={loadingBookings || bookingOptions.length === 0}
                    />
                </div>
                <div style={{ marginBottom: '10px' }}>
                    <label htmlFor="booking2SelectSwap" style={{ display: 'block', marginBottom: '4px' }}>Select Second Booking:</label>
                    <Select
                        inputId="booking2SelectSwap"
                        value={selectedBooking2}
                        onChange={setSelectedBooking2}
                        options={bookingOptions.filter((opt) => opt.value !== selectedBooking1?.value)}
                        isClearable
                        isSearchable
                        placeholder="Select Booking 2..."
                        isDisabled={loadingBookings || bookingOptions.length === 0}
                    />
                </div>
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
