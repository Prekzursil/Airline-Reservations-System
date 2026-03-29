import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { fetchAirplanes, fetchAirplaneDetails } from '../services/apiService';
import SeatMap from './SeatMap';

/**
 * Displays the list of flights and loads seat maps for the selected flight.
 *
 * @param {object} props Component props.
 * @param {?Function} props.onBookingListChanged Optional callback fired after booking changes.
 * @returns {JSX.Element} The rendered flight list.
 */
const FlightList = ({ onBookingListChanged = null }) => {
    const [airplanes, setAirplanes] = useState([]);
    const [selectedFlight, setSelectedFlight] = useState(null);
    const [flightDetails, setFlightDetails] = useState(null);
    const [loadingDetails, setLoadingDetails] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        /**
         * Loads the current airplane list from the API.
         *
         * @returns {Promise<void>} A promise that settles after loading completes.
         */
        const loadAirplanes = async () => {
            try {
                const data = await fetchAirplanes();
                setAirplanes(data);
            } catch {
                setError('Failed to load airplanes. Ensure the C++ API server is running.');
            }
        };
        loadAirplanes();
    }, []);

    /**
     * Selects a flight and toggles its detail pane.
     *
     * @param {string} flightNumber The flight to load.
     * @param {boolean} forceRefresh Whether the current detail pane should be reloaded.
     * @returns {Promise<void>} A promise that settles after the detail request completes.
     */
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
        } catch {
            setError(`Failed to load details for flight ${flightNumber}.`);
            if (selectedFlight !== flightNumber) {
                setFlightDetails(null);
            }
        } finally {
            setLoadingDetails(false);
        }
    };

    /**
     * Refreshes the flight list after a successful seat booking.
     *
     * @param {string} flightNumberOfBooking The flight that was updated.
     */
    const handleBookingSuccess = (flightNumberOfBooking) => {
        fetchAirplanes().then(setAirplanes).catch(() => {
            setError('Failed to refresh airplane list after booking.');
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
