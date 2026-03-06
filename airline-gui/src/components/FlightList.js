import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { fetchAirplanes, fetchAirplaneDetails } from '../services/apiService';
import SeatMap from './SeatMap';

const FlightList = ({ onBookingListChanged = null }) => {
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
            setSelectedFlight(null);
            setFlightDetails(null);
            return;
        }

        setSelectedFlight(flightNumber);
        setLoadingDetails(true);
        setError('');
        try {
            const data = await fetchAirplaneDetails(flightNumber);
            setFlightDetails(data);
        } catch (err) {
            setError(`Failed to load details for flight ${flightNumber}.`);
            console.error(err);
            if (selectedFlight !== flightNumber) {
                setFlightDetails(null);
            }
        } finally {
            setLoadingDetails(false);
        }
    };

    const handleBookingSuccess = (flightNumberOfBooking) => {
        fetchAirplanes().then(setAirplanes).catch((err) => {
            setError('Failed to refresh airplane list after booking.');
            console.error(err);
        });

        if (selectedFlight === flightNumberOfBooking) {
            handleFlightSelect(flightNumberOfBooking, true);
        }
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
                {airplanes.map((plane) => {
                    const isExpanded = selectedFlight === plane.flightNumber;
                    return (
                        <li key={plane.flightNumber} style={{ marginBottom: '10px' }}>
                            <button
                                type="button"
                                onClick={() => handleFlightSelect(plane.flightNumber, false)}
                                aria-expanded={isExpanded}
                                aria-controls={`flight-details-${plane.flightNumber}`}
                            >
                                {plane.flightNumber} (Capacity: {plane.capacity}, Booked: {plane.bookedSeatsCount})
                            </button>
                        </li>
                    );
                })}
            </ul>

            {loadingDetails && <p>Loading flight details...</p>}

            {selectedFlight && flightDetails && (
                <div id={`flight-details-${selectedFlight}`}>
                    <h3>Details for Flight: {selectedFlight}</h3>
                    <SeatMap
                        seats={flightDetails.seats}
                        flightNumber={selectedFlight}
                        onBookingSuccess={handleBookingSuccess}
                    />
                </div>
            )}
        </div>
    );
};

FlightList.propTypes = {
    onBookingListChanged: PropTypes.func,
};

export default FlightList;
