import React, { useState, useEffect } from 'react';
import Select from 'react-select';
import { swapSeats, fetchBookings } from '../services/apiService';

const SwapSeatsForm = ({ onSeatsSwapped, refreshTrigger }) => { // Added refreshTrigger prop
    const [allBookings, setAllBookings] = useState([]);
    const [selectedBooking1, setSelectedBooking1] = useState(null); // { value, label }
    const [selectedBooking2, setSelectedBooking2] = useState(null); // { value, label }
    const [statusMessage, setStatusMessage] = useState('');
    const [loadingBookings, setLoadingBookings] = useState(false);
    const [errorLoadingBookings, setErrorLoadingBookings] = useState('');

    useEffect(() => {
        console.log("SwapSeatsForm useEffect triggered, refreshTrigger:", refreshTrigger); // DEBUG
        const loadBookings = async () => {
            setLoadingBookings(true);
            setErrorLoadingBookings('');
            try {
                const bookingsData = await fetchBookings();
                setAllBookings(bookingsData || []);
            } catch (error) {
                console.error("Failed to fetch bookings for swap form:", error);
                setErrorLoadingBookings('Could not load bookings.');
                setAllBookings([]);
            } finally {
                setLoadingBookings(false);
            }
        };
        loadBookings();
    }, [refreshTrigger]); // Add refreshTrigger to dependency array

    const bookingOptions = allBookings
        .filter(b => b.status === "Confirmed") // Match case from API "Confirmed"
        .map(b => ({
            value: b.bookingId,
            label: `ID: ${b.bookingId} (Cust: ${b.customerId}, Flight: ${b.flightNumber}, Seat: ${b.seatId})`
        }));

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!selectedBooking1 || !selectedBooking1.value || !selectedBooking2 || !selectedBooking2.value) {
            setStatusMessage('Please select both bookings.');
            return;
        }
        if (selectedBooking1.value === selectedBooking2.value) {
            setStatusMessage('Booking IDs must be different.');
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
            {loadingBookings && <p>Loading bookings...</p>}
            {errorLoadingBookings && <p style={{color: 'red'}}>{errorLoadingBookings}</p>}
            {!loadingBookings && !errorLoadingBookings && allBookings.length === 0 && <p>No confirmed bookings available to swap.</p>}
            
            <form onSubmit={handleSubmit} style={{opacity: loadingBookings || allBookings.length === 0 ? 0.5 : 1}}>
                <div style={{ marginBottom: '10px' }}>
                    <label htmlFor="booking1SelectSwap">Select First Booking: </label>
                    <Select
                        id="booking1SelectSwap"
                        value={selectedBooking1}
                        onChange={setSelectedBooking1}
                        options={bookingOptions.filter(opt => !selectedBooking2 || opt.value !== selectedBooking2.value)}
                        isClearable
                        isSearchable
                        placeholder="Select Booking 1..."
                        isDisabled={loadingBookings || bookingOptions.length === 0}
                        styles={{ container: base => ({ ...base, width: '100%', maxWidth: '500px' }) }}
                    />
                </div>
                <div style={{ marginBottom: '10px' }}>
                    <label htmlFor="booking2SelectSwap">Select Second Booking: </label>
                    <Select
                        id="booking2SelectSwap"
                        value={selectedBooking2}
                        onChange={setSelectedBooking2}
                        options={bookingOptions.filter(opt => !selectedBooking1 || opt.value !== selectedBooking1.value)}
                        isClearable
                        isSearchable
                        placeholder="Select Booking 2..."
                        isDisabled={loadingBookings || bookingOptions.length === 0}
                        styles={{ container: base => ({ ...base, width: '100%', maxWidth: '500px' }) }}
                    />
                </div>
                <button type="submit" style={{marginTop: '10px'}} disabled={loadingBookings || !selectedBooking1 || !selectedBooking2}>
                    Swap Selected Seats
                </button>
            </form>
            {statusMessage && <p>{statusMessage}</p>}
        </div>
    );
};

export default SwapSeatsForm;
