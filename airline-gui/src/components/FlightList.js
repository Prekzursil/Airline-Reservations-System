import React, { useState, useEffect } from 'react';
import { fetchAirplanes, fetchAirplaneDetails } from '../services/apiService';
import SeatMap from './SeatMap'; 

const FlightList = ({ onBookingListChanged }) => { // Accept onBookingListChanged prop
    const [airplanes, setAirplanes] = useState([]);
    const [selectedFlight, setSelectedFlight] = useState(null);
    const [flightDetails, setFlightDetails] = useState(null);
    const [loadingDetails, setLoadingDetails] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        const loadAirplanes = async () => {
            try {
                const data = await fetchAirplanes();
                setAirplanes(data);
            } catch (err) {
                setError('Failed to load airplanes. Ensure the C++ API server is running.');
                console.error(err);
            }
        };
        loadAirplanes();
    }, []);

    const handleFlightSelect = async (flightNumber, forceRefresh = false) => {
        if (selectedFlight === flightNumber && !forceRefresh) {
            // Toggle off if already selected and not a forced refresh
            setSelectedFlight(null);
            setFlightDetails(null);
            return;
        }
        
        // If it's a new selection or a forced refresh for the current flight
        setSelectedFlight(flightNumber); // Ensure it's set/remains set
        setLoadingDetails(true);
        setError('');
        try {
            const data = await fetchAirplaneDetails(flightNumber);
            setFlightDetails(data); // Update details
        } catch (err) {
            setError(`Failed to load details for flight ${flightNumber}.`);
            console.error(err);
            // Don't nullify flightDetails if it's a refresh attempt that failed,
            // unless it was a new selection.
            if (selectedFlight !== flightNumber) { // if it was a new selection that failed
                 setFlightDetails(null);
            }
        } finally {
            setLoadingDetails(false);
        }
    };
    
    const handleBookingSuccess = (flightNumberOfBooking) => {
        // Refresh the main airplane list to update bookedSeatsCount
        fetchAirplanes().then(setAirplanes).catch(err => {
            setError('Failed to refresh airplane list after booking.');
            console.error(err);
        });

        // If the booked flight is currently selected, force refresh its details
        if (selectedFlight === flightNumberOfBooking) {
            handleFlightSelect(flightNumberOfBooking, true);
        }
        // Also, notify App.js that the booking list might have changed
        if (onBookingListChanged) {
            onBookingListChanged();
        }
    };

    if (error) {
        return <p style={{ color: 'red' }}>Error: {error}</p>;
    }

    return (
        <div>
            <h2>Available Flights</h2>
            {airplanes.length === 0 && !error && <p>Loading flights or no flights available...</p>}
            <ul>
                {airplanes.map((plane) => (
                    <li key={plane.flightNumber} style={{ marginBottom: '10px' }}>
                        <button onClick={() => handleFlightSelect(plane.flightNumber, false)}>
                            {plane.flightNumber} (Capacity: {plane.capacity}, Booked: {plane.bookedSeatsCount})
                        </button>
                    </li>
                ))}
            </ul>

            {loadingDetails && <p>Loading flight details...</p>}
            
            {selectedFlight && flightDetails && (
                <div>
                    <h3>Details for Flight: {selectedFlight}</h3>
                    <SeatMap 
                        seats={flightDetails.seats} 
                        flightNumber={selectedFlight} 
                        onBookingSuccess={handleBookingSuccess} // Use new handler
                    />
                </div>
            )}
        </div>
    );
};

export default FlightList;
