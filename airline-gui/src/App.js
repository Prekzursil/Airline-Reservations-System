import React, { useEffect, useState } from 'react';
import './App.css';
import FlightList from './components/FlightList';
import CustomerForm from './components/CustomerForm';
import CustomerDetails from './components/CustomerDetails';
import SwapSeatsForm from './components/SwapSeatsForm';
import { fetchCustomers } from './services/apiService';

const customerPanelStyle = { flex: 1, border: '1px solid #ccc', padding: '15px' };
const bookingPanelStyle = { flex: 2, border: '1px solid #ccc', padding: '15px' };
const mainLayoutStyle = { padding: '20px', display: 'flex', gap: '20px' };
const customerSectionStyle = { marginBottom: '20px' };
const customerButtonStyle = {
  cursor: 'pointer',
  border: 'none',
  background: 'transparent',
  padding: 0,
  font: 'inherit',
  color: 'inherit',
  textAlign: 'left',
};

function CustomerListSection({
  customerError,
  customers,
  loadCustomers,
  selectedCustomerId,
  showCustomers,
  onCustomerSelect,
}) {
  return (
    <section style={customerSectionStyle}>
      <button type="button" onClick={loadCustomers} style={{ marginRight: '10px' }}>
        {showCustomers ? 'Refresh Customer List' : 'Show Customer List'}
      </button>
      {customerError && <p aria-live="polite" style={{ color: 'red' }}>{customerError}</p>}
      {showCustomers && customers.length > 0 && (
        <div>
          <h3>All Customers:</h3>
          <ul>
            {customers.map((cust) => (
              <li key={cust.personId}>
                <button
                  type="button"
                  onClick={() => onCustomerSelect(cust.personId)}
                  aria-pressed={selectedCustomerId === cust.personId}
                  aria-controls={selectedCustomerId === cust.personId ? 'customer-details-panel' : undefined}
                  style={customerButtonStyle}
                >
                  {cust.name} (ID: {cust.personId})
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {showCustomers && customers.length === 0 && !customerError && <p>No customers found.</p>}
    </section>
  );
}

function CustomerSearchSection({
  customerDetailsRefreshKey,
  onBookingCancelled,
  onSearchCustomer,
  searchCustomerId,
  selectedCustomerId,
  setSearchCustomerId,
}) {
  return (
    <section>
      <h3>View Specific Customer Details</h3>
      <label htmlFor="searchCustomerIdInput" style={{ marginRight: '10px' }}>
        Customer ID
      </label>
      <input
        id="searchCustomerIdInput"
        type="text"
        value={searchCustomerId}
        onChange={(event) => setSearchCustomerId(event.target.value)}
        placeholder="Enter Customer ID"
        style={{ marginRight: '10px' }}
      />
      <button type="button" onClick={onSearchCustomer}>Search Customer</button>
      {selectedCustomerId && (
        <div id="customer-details-panel">
          <CustomerDetails
            customerId={selectedCustomerId}
            onBookingCancelled={onBookingCancelled}
            refreshTrigger={customerDetailsRefreshKey}
          />
        </div>
      )}
    </section>
  );
}

function BookingManagementSection({ bookingsRefreshKey, onSeatsSwapped, swapStatusMessage, triggerBookingsRefresh }) {
  return (
    <div style={bookingPanelStyle}>
      <h2>Flight & Booking Management</h2>
      <FlightList onBookingListChanged={triggerBookingsRefresh} />
      <section style={{ marginTop: '20px', padding: '15px', border: '1px solid #eee' }}>
        <SwapSeatsForm onSeatsSwapped={onSeatsSwapped} refreshTrigger={bookingsRefreshKey} />
        {swapStatusMessage && <p aria-live="polite">{swapStatusMessage}</p>}
      </section>
    </div>
  );
}

/**
 * Renders the airline reservation dashboard and coordinates cross-panel refreshes.
 *
 * @returns {JSX.Element} The application shell.
 */
function App() {
  const [customers, setCustomers] = useState([]);
  const [showCustomers, setShowCustomers] = useState(false);
  const [customerError, setCustomerError] = useState('');
  const [selectedCustomerId, setSelectedCustomerId] = useState('');
  const [searchCustomerId, setSearchCustomerId] = useState('');
  const [bookingsRefreshKey, setBookingsRefreshKey] = useState(0);
  const [customerDetailsRefreshKey, setCustomerDetailsRefreshKey] = useState(0);
  const [swapStatusMessage, setSwapStatusMessage] = useState('');

  /**
   * Loads the current customer list from the API.
   *
   * @returns {Promise<void>} A promise that settles after the refresh completes.
   */
  const loadCustomers = async () => {
    try {
      setCustomerError('');
      const data = await fetchCustomers();
      setCustomers(data);
      setShowCustomers(true);
    } catch {
      setCustomerError('Failed to load customers. Ensure API server is running.');
      setShowCustomers(false);
    }
  };

  /**
   * Increments the booking refresh token shared across dependent views.
   */
  const incrementBookingsRefreshKey = () => {
    setBookingsRefreshKey((prevKey) => prevKey + 1);
  };

  /**
   * Selects a customer from the list and mirrors that value into the search field.
   *
   * @param {string} customerId The selected customer identifier.
   */
  const handleCustomerSelect = (customerId) => {
    setSwapStatusMessage('');
    setSearchCustomerId(customerId);
    setSelectedCustomerId(customerId);
  };

  /**
   * Refreshes customer-dependent views after a new customer is created.
   */
  const handleCustomerAdded = () => {
    setSwapStatusMessage('');
    loadCustomers();
    incrementBookingsRefreshKey();
  };

  /**
   * Refreshes booking-driven views after downstream booking changes.
   */
  const triggerBookingsRefresh = () => {
    setSwapStatusMessage('');
    incrementBookingsRefreshKey();
  };

  /**
   * Loads the currently typed customer identifier into the detail pane.
   */
  const handleSearchCustomer = () => {
    setSwapStatusMessage('');
    setSelectedCustomerId(searchCustomerId);
  };

  /**
   * Refreshes both customer details and booking lists after a booking mutation.
   *
   * @param {string} customerId The customer whose detail pane should be refreshed.
   */
  const refreshCustomerDetails = (customerId) => {
    setSwapStatusMessage('');
    setSelectedCustomerId(customerId);
    setCustomerDetailsRefreshKey((prevKey) => prevKey + 1);
    loadCustomers();
    incrementBookingsRefreshKey();
  };

  /**
   * Refreshes the booking panels after a seat swap and reports the outcome inline.
   */
  const handleSeatsSwapped = () => {
    if (selectedCustomerId) {
      refreshCustomerDetails(selectedCustomerId);
    } else {
      setSwapStatusMessage('');
      loadCustomers();
      incrementBookingsRefreshKey();
    }
    setSwapStatusMessage(
      'Seats swapped. Customer details and booking lists were refreshed. Re-select the flight if you need a fresh seat map.'
    );
  };

  useEffect(() => {
    loadCustomers();
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>Airline Reservation System GUI</h1>
      </header>
      <main style={mainLayoutStyle}>
        <div style={customerPanelStyle}>
          <h2>Customer Management</h2>
          <section style={customerSectionStyle}>
            <CustomerForm onCustomerAdded={handleCustomerAdded} />
          </section>
          <CustomerListSection
            customerError={customerError}
            customers={customers}
            loadCustomers={loadCustomers}
            selectedCustomerId={selectedCustomerId}
            showCustomers={showCustomers}
            onCustomerSelect={handleCustomerSelect}
          />
          <CustomerSearchSection
            customerDetailsRefreshKey={customerDetailsRefreshKey}
            onBookingCancelled={refreshCustomerDetails}
            onSearchCustomer={handleSearchCustomer}
            searchCustomerId={searchCustomerId}
            selectedCustomerId={selectedCustomerId}
            setSearchCustomerId={setSearchCustomerId}
          />
        </div>
        <BookingManagementSection
          bookingsRefreshKey={bookingsRefreshKey}
          onSeatsSwapped={handleSeatsSwapped}
          swapStatusMessage={swapStatusMessage}
          triggerBookingsRefresh={triggerBookingsRefresh}
        />
      </main>
    </div>
  );
}

export default App;
