import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { fetchCustomerDetails, cancelBooking as apiCancelBooking } from '../services/apiService';

/**
 * Renders the selected customer profile and manages booking cancellation flows.
 *
 * @param {object} props Component props.
 * @param {string} props.customerId The customer identifier to load.
 * @param {?Function} props.onBookingCancelled Optional callback invoked after a successful cancellation.
 * @param {number|string} props.refreshTrigger Token used to force reloads for the same customer.
 * @returns {JSX.Element} The rendered customer details panel.
 */
const CustomerDetails = ({ customerId, onBookingCancelled = null, refreshTrigger = 0 }) => {
  const [customer, setCustomer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [actionStatus, setActionStatus] = useState('');
  const [pendingCancellationId, setPendingCancellationId] = useState(null);

  useEffect(() => {
    if (customerId) {
      /**
       * Loads the customer detail payload for the current selection.
       *
       * @returns {Promise<void>} A promise that settles after the detail request completes.
       */
      const loadDetails = async () => {
        setLoading(true);
        setError('');
        setActionStatus('');
        setPendingCancellationId(null);
        try {
          const data = await fetchCustomerDetails(customerId);
          setCustomer(data);
        } catch (err) {
          setError(`Failed to load details for customer ${customerId}: ${err.message}`);
          setCustomer(null);
        } finally {
          setLoading(false);
        }
      };
      loadDetails();
    } else {
      setCustomer(null);
      setPendingCancellationId(null);
    }
  }, [customerId, refreshTrigger]);

  /**
   * Starts the inline confirmation flow for a booking cancellation.
   *
   * @param {number|string} bookingId The booking being targeted for cancellation.
   */
  const requestBookingCancellation = (bookingId) => {
    setPendingCancellationId(bookingId);
    setActionStatus(`Confirm cancellation for booking ${bookingId}.`);
  };

  /**
   * Clears the pending inline cancellation prompt.
   */
  const keepBooking = () => {
    setPendingCancellationId(null);
    setActionStatus('Cancellation kept.');
  };

  /**
   * Cancels a booking after the inline confirmation step.
   *
   * @param {number|string} bookingId The booking being cancelled.
   * @returns {Promise<void>} A promise that settles after the cancellation request completes.
   */
  const handleCancelBooking = async (bookingId) => {
    setActionStatus(`Cancelling booking ${bookingId}...`);
    try {
      const result = await apiCancelBooking(bookingId);
      setPendingCancellationId(null);
      setActionStatus(result.message || `Booking ${bookingId} cancellation processed.`);
      if (onBookingCancelled) {
        onBookingCancelled(customerId);
      }
    } catch (err) {
      setPendingCancellationId(null);
      setActionStatus(`Failed to cancel booking ${bookingId}: ${err.message}`);
    }
  };

  if (!customerId) {
    return <p>Select or enter a customer ID to view details.</p>;
  }
  if (loading) {
    return <p>Loading customer details...</p>;
  }
  if (error) {
    return <p style={{ color: 'red' }}>{error}</p>;
  }
  if (!customer) {
    return <p>No customer data found for ID: {customerId}.</p>;
  }

  return (
    <div>
      <h4>
        Customer Details: {customer.name} (ID: {customer.personId})
      </h4>
      <p>Age: {customer.age}</p>
      <p>Money: ${customer.money.toFixed(2)}</p>
      <h5>Bookings:</h5>
      {customer.bookings && customer.bookings.length > 0 ? (
        <ul>
          {customer.bookings.map((booking) => (
            <li key={booking.bookingId}>
              ID: {booking.bookingId}, Flight: {booking.flightNumber}, Seat: {booking.seatId},
              Status: {booking.status}
              {booking.status !== 'CANCELLED' &&
                (pendingCancellationId === booking.bookingId ? (
                  <>
                    <button
                      type="button"
                      onClick={() => handleCancelBooking(booking.bookingId)}
                      aria-label={`Confirm cancellation for booking ${booking.bookingId}`}
                      style={{ marginLeft: '10px' }}
                    >
                      Confirm Cancel
                    </button>
                    <button
                      type="button"
                      onClick={keepBooking}
                      aria-label={`Keep booking ${booking.bookingId}`}
                      style={{ marginLeft: '10px' }}
                    >
                      Keep Booking
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={() => requestBookingCancellation(booking.bookingId)}
                    aria-label={`Cancel booking ${booking.bookingId}`}
                    style={{ marginLeft: '10px' }}
                  >
                    Cancel Booking
                  </button>
                ))}
            </li>
          ))}
        </ul>
      ) : (
        <p>No bookings found for this customer.</p>
      )}
      {actionStatus && (
        <p aria-live="polite">
          <em>{actionStatus}</em>
        </p>
      )}
    </div>
  );
};

CustomerDetails.propTypes = {
  customerId: PropTypes.string,
  onBookingCancelled: PropTypes.func,
  refreshTrigger: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
};

export default CustomerDetails;
