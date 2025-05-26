import React, { useState, useEffect } from 'react';
import Select from 'react-select'; 
import { createBooking, fetchCustomers, cancelBooking as apiCancelBooking } from '../services/apiService';

const SeatMap = ({ seats, flightNumber, onBookingSuccess }) => {
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
                console.error("Failed to load customers for dropdown:", error);
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
    if (currentRow.length > 0) {
        rows.push(currentRow);
    }

    const handleSeatClick = (seat) => {
        if (seat.isBooked) {
            console.log("Clicked booked seat object:", seat); 
            let statusMsg = `Seat ${seat.seatId}: This seat is already booked.`;
            if (seat.bookedByCustomerId) {
                statusMsg = `Seat ${seat.seatId}: Booked by Customer ID ${seat.bookedByCustomerId}.`;
                // Cancel button is now rendered directly on the seat if seat.bookingId exists
            }
            setBookingStatus(statusMsg);
            setSelectedSeatId(null); 
            return;
        }
        setSelectedSeatId(seat.seatId);
        setBookingStatus(`Selected seat: ${seat.seatId} (${seat.seatClass}, Price: $${seat.price})`);
    };

    const handleCancelBookingFromSeat = async (bookingIdToCancel) => {
        if (!bookingIdToCancel) return;
        if (!window.confirm(`Are you sure you want to cancel booking ${bookingIdToCancel} for this seat?`)) {
            return;
        }
        setBookingStatus(`Cancelling booking ${bookingIdToCancel}...`);
        try {
            const result = await apiCancelBooking(bookingIdToCancel);
            setBookingStatus(result.message || `Booking ${bookingIdToCancel} cancellation processed.`);
            if (onBookingSuccess) { 
                onBookingSuccess(flightNumber); // Re-use to refresh flight details
            }
        } catch (err) {
            setBookingStatus(`Failed to cancel booking ${bookingIdToCancel}: ${err.message}`);
            console.error("Cancellation error from seat map:", err);
        }
    };

    const handleConfirmBooking = async () => {
        if (!selectedSeatId) {
            setBookingStatus('Please select a seat first.');
            return;
        }
        if (!customerIdForBooking || !customerIdForBooking.value) {
            setBookingStatus('Please select a Customer for booking.');
            return;
        }

        const bookingData = {
            customerId: customerIdForBooking.value, 
            flightNumber: flightNumber,
            seatId: selectedSeatId,
        };
        try {
            setBookingStatus('Processing booking...');
            const result = await createBooking(bookingData);
            setBookingStatus(`Booking successful! ID: ${result.bookingId}. Seat: ${result.seatId} for Customer: ${result.customerId}`);
            
            setSelectedSeatId(null); 
            setCustomerIdForBooking(null); 
            
            if(onBookingSuccess) { 
                onBookingSuccess(flightNumber); 
            }
        } catch (error) {
            setBookingStatus(`Booking failed: ${error.message}`);
            console.error("Booking error:", error);
        }
    };
    
    const getSeatStyle = (seat) => {
        let backgroundColor = 'lightgreen'; 
        if (seat.isBooked) backgroundColor = 'lightcoral'; 
        else if (seat.seatClass === 'Business') backgroundColor = 'lightblue'; 
        
        if (seat.seatId === selectedSeatId) backgroundColor = 'yellow'; 

        return {
            width: '60px', // Slightly wider to accommodate cancel button
            height: '60px', // Slightly taller
            margin: '5px',
            border: '1px solid #ccc',
            backgroundColor: backgroundColor,
            // cursor: seat.isBooked ? 'not-allowed' : 'pointer', // Removed, handled by button inside
            display: 'flex',
            flexDirection: 'column', // To stack seatId and cancel button
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.8em',
            position: 'relative' // For potential absolute positioning of cancel button if needed
        };
    };

    return (
        <div>
            <h4>Seat Map for {flightNumber}</h4>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                {rows.map((row, rowIndex) => (
                    <div key={rowIndex} style={{ display: 'flex' }}>
                        {row.map(seat => (
                            <div // Changed from button to div to allow nested button
                                key={seat.seatId} 
                                style={getSeatStyle(seat)}
                                onClick={() => handleSeatClick(seat)}
                            >
                                {seat.seatId}
                                {seat.isBooked && seat.bookingId && (
                                    <button 
                                        onClick={(e) => {
                                            e.stopPropagation(); 
                                            handleCancelBookingFromSeat(seat.bookingId);
                                        }}
                                        style={{fontSize: '0.6em', padding: '1px 3px', marginTop: '3px', cursor: 'pointer'}}
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
            {bookingStatus && <p>{bookingStatus}</p>}
            {customerLoadingError && <p style={{color: 'red'}}>{customerLoadingError}</p>}
            {selectedSeatId && (
                <div style={{marginTop: '10px'}}>
                    <label htmlFor="customerSelectBooking">Select Customer: </label>
                    {loadingCustomers ? (
                        <span>Loading customers...</span>
                    ) : (
                        <Select
                            id="customerSelectBooking"
                            value={customerIdForBooking}
                            onChange={setCustomerIdForBooking} 
                            options={customers.map(cust => ({ value: cust.personId, label: `${cust.name} (ID: ${cust.personId})` }))}
                            isClearable
                            isSearchable
                            placeholder="Select or type to search Customer..."
                            isDisabled={customers.length === 0 && !customerLoadingError}
                            styles={{ container: base => ({ ...base, width: '300px', marginRight: '10px', display: 'inline-block' }) }}
                        />
                    )}
                    <button onClick={handleConfirmBooking} disabled={!customerIdForBooking || !customerIdForBooking.value || loadingCustomers}>
                        Confirm Booking for {selectedSeatId}
                    </button>
                </div>
            )}
            <div style={{marginTop: '10px'}}>
                Legend: 
                <span style={{backgroundColor: 'lightgreen', padding: '2px 5px', margin: '0 5px'}}>Available Economy</span>
                <span style={{backgroundColor: 'lightblue', padding: '2px 5px', margin: '0 5px'}}>Available Business</span>
                <span style={{backgroundColor: 'lightcoral', padding: '2px 5px', margin: '0 5px'}}>Booked</span>
                <span style={{backgroundColor: 'yellow', padding: '2px 5px', margin: '0 5px'}}>Selected</span>
            </div>
        </div>
    );
};

export default SeatMap;
