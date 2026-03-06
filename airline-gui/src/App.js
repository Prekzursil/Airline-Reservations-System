import React, { useEffect, useState } from 'react';
import './App.css';
import FlightList from './components/FlightList';
import CustomerForm from './components/CustomerForm';
import CustomerDetails from './components/CustomerDetails';
import SwapSeatsForm from './components/SwapSeatsForm';
import { fetchCustomers } from './services/apiService';

function App() {
  const [customers, setCustomers] = useState([]);
  const [showCustomers, setShowCustomers] = useState(false);
  const [customerError, setCustomerError] = useState('');
  const [selectedCustomerId, setSelectedCustomerId] = useState('');
  const [searchCustomerId, setSearchCustomerId] = useState('');
  const [bookingsRefreshKey, setBookingsRefreshKey] = useState(0);
  const [customerDetailsRefreshKey, setCustomerDetailsRefreshKey] = useState(0);

  const loadCustomers = async () => {
    try {
      setCustomerError('');
      const data = await fetchCustomers();
      setCustomers(data);
      setShowCustomers(true);
    } catch (err) {
      setCustomerError('Failed to load customers. Ensure API server is running.');
      console.error(err);
      setShowCustomers(false);
    }
  };

  const incrementBookingsRefreshKey = () => {
    setBookingsRefreshKey((prevKey) => prevKey + 1);
  };

  const handleCustomerSelect = (customerId) => {
    setSearchCustomerId(customerId);
    setSelectedCustomerId(customerId);
  };

  const handleCustomerAdded = () => {
    loadCustomers();
    incrementBookingsRefreshKey();
  };

  const triggerBookingsRefresh = () => {
    incrementBookingsRefreshKey();
  };

  const handleSearchCustomer = () => {
    setSelectedCustomerId(searchCustomerId);
  };
  
  const refreshCustomerDetails = (customerId) => {
    setSelectedCustomerId(customerId);
    setCustomerDetailsRefreshKey((prevKey) => prevKey + 1);
    loadCustomers();
    incrementBookingsRefreshKey();
  };

  const handleSeatsSwapped = () => {
    if (selectedCustomerId) {
      refreshCustomerDetails(selectedCustomerId);
    } else {
      loadCustomers();
      incrementBookingsRefreshKey();
    }
    alert("Seats swapped. Customer details (if viewing) and booking lists refreshed. You may need to re-select a flight to see seat map updates.");
  };

  useEffect(() => {
    loadCustomers();
  }, []);


  return (
    <div className="App">
      <header className="App-header">
        <h1>Airline Reservation System GUI</h1>
      </header>
      <main style={{ padding: '20px', display: 'flex', gap: '20px' }}>
        <div style={{ flex: 1, border: '1px solid #ccc', padding: '15px' }}>
          <h2>Customer Management</h2>
          <section style={{ marginBottom: '20px' }}>
            <CustomerForm onCustomerAdded={handleCustomerAdded} />
          </section>

          <section style={{ marginBottom: '20px' }}>
            <button type="button" onClick={loadCustomers} style={{marginRight: '10px'}}>
              {showCustomers ? 'Refresh Customer List' : 'Show Customer List'}
            </button>
            {customerError && <p aria-live="polite" style={{color: 'red'}}>{customerError}</p>}
            {showCustomers && customers.length > 0 && (
              <div>
                <h3>All Customers:</h3>
                <ul>
                  {customers.map((cust) => (
                    <li key={cust.personId}>
                      <button
                        type="button"
                        onClick={() => handleCustomerSelect(cust.personId)}
                        aria-pressed={selectedCustomerId === cust.personId}
                        aria-controls={selectedCustomerId === cust.personId ? 'customer-details-panel' : undefined}
                        style={{
                          cursor: 'pointer',
                          border: 'none',
                          background: 'transparent',
                          padding: 0,
                          font: 'inherit',
                          color: 'inherit',
                          textAlign: 'left',
                        }}
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

          <section>
            <h3>View Specific Customer Details</h3>
            <label htmlFor="searchCustomerIdInput" style={{ marginRight: '10px' }}>
              Customer ID
            </label>
            <input
              id="searchCustomerIdInput"
              type="text"
              value={searchCustomerId}
              onChange={(e) => setSearchCustomerId(e.target.value)}
              placeholder="Enter Customer ID"
              style={{ marginRight: '10px' }}
            />
            <button type="button" onClick={handleSearchCustomer}>Search Customer</button>
            {selectedCustomerId && (
              <div id="customer-details-panel">
                <CustomerDetails
                  customerId={selectedCustomerId}
                  onBookingCancelled={refreshCustomerDetails}
                  refreshTrigger={customerDetailsRefreshKey}
                />
              </div>
            )}
          </section>
        </div>
        
        <div style={{ flex: 2, border: '1px solid #ccc', padding: '15px' }}>
          <h2>Flight & Booking Management</h2>
          <FlightList onBookingListChanged={triggerBookingsRefresh} />
          <section style={{ marginTop: '20px', padding: '15px', border: '1px solid #eee' }}>
            <SwapSeatsForm onSeatsSwapped={handleSeatsSwapped} refreshTrigger={bookingsRefreshKey} />
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;
