import React, { useState, useEffect } from 'react';
import './App.css';
import FlightList from './components/FlightList';
import CustomerForm from './components/CustomerForm';
import CustomerDetails from './components/CustomerDetails';
import SwapSeatsForm from './components/SwapSeatsForm'; // Import SwapSeatsForm
import { fetchCustomers } from './services/apiService'; 

function App() {
  const [customers, setCustomers] = useState([]);
  const [showCustomers, setShowCustomers] = useState(false);
  const [customerError, setCustomerError] = useState('');
  const [selectedCustomerId, setSelectedCustomerId] = useState(''); // For CustomerDetails
  const [searchCustomerId, setSearchCustomerId] = useState(''); // Input field for customer search
  const [bookingsRefreshKey, setBookingsRefreshKey] = useState(0); // Key to trigger bookings refresh

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

  const handleCustomerAdded = (newCustomer) => {
    // Optionally refresh customer list or add to existing list
    // For simplicity, just log or allow manual refresh for now
    console.log("New customer added/simulated:", newCustomer);
    // If we want to auto-refresh:
    loadCustomers(); // Refresh customer list after adding
    console.log("App.js: handleCustomerAdded, incrementing bookingsRefreshKey"); // DEBUG
    setBookingsRefreshKey(prevKey => prevKey + 1); // Trigger refresh for SwapSeatsForm
  };

  const triggerBookingsRefresh = () => { // New function
    console.log("App.js: triggerBookingsRefresh called, incrementing bookingsRefreshKey"); // DEBUG
    setBookingsRefreshKey(prevKey => prevKey + 1);
  };

  const handleSearchCustomer = () => {
    setSelectedCustomerId(searchCustomerId);
  };
  
  // Callback for when a booking is cancelled in CustomerDetails, to refresh data
  const refreshCustomerDetails = (customerId) => {
    // To refresh, we can briefly unset and then set customerId, or add a random key to CustomerDetails
    // For simplicity, just re-trigger the fetch in CustomerDetails by changing customerId prop slightly if needed
    // Or, CustomerDetails already re-fetches if customerId prop changes.
    // If the same customerId is passed, useEffect in CustomerDetails might not re-run.
    // A simple way:
    const currentSelected = selectedCustomerId; 
    setSelectedCustomerId(''); 
    setTimeout(() => setSelectedCustomerId(currentSelected || customerId), 0); 
    loadCustomers(); 
    console.log("App.js: refreshCustomerDetails, incrementing bookingsRefreshKey"); // DEBUG
    setBookingsRefreshKey(prevKey => prevKey + 1); // Trigger refresh for SwapSeatsForm
  };

  const handleSeatsSwapped = () => {
    // After seats are swapped, relevant data might change for customers or flights
    console.log("App.js: handleSeatsSwapped, preparing to refresh bookingsRefreshKey"); // DEBUG
    if (selectedCustomerId) {
        refreshCustomerDetails(selectedCustomerId); // This will also update bookingsRefreshKey
    } else {
        loadCustomers(); // Refresh general customer list
        setBookingsRefreshKey(prevKey => prevKey + 1); 
    }
    // FlightList also needs to be aware or refreshed if a swap affects seat availability display
    // For now, the alert prompts manual refresh of flight details if needed.
    alert("Seats swapped. Customer details (if viewing) and booking lists refreshed. You may need to re-select a flight to see seat map updates.");
  };

  // Load initial customers once
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
            <button onClick={loadCustomers} style={{marginRight: '10px'}}>
              {showCustomers ? 'Refresh Customer List' : 'Show Customer List'}
            </button>
            {customerError && <p style={{color: 'red'}}>{customerError}</p>}
            {showCustomers && customers.length > 0 && (
              <div>
                <h3>All Customers:</h3>
                <ul>
                  {customers.map(cust => (
                    <li key={cust.personId} onClick={() => {setSearchCustomerId(cust.personId); setSelectedCustomerId(cust.personId);}} style={{cursor: 'pointer'}}>
                      {cust.name} (ID: {cust.personId})
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {showCustomers && customers.length === 0 && !customerError && <p>No customers found.</p>}
          </section>

          <section>
            <h3>View Specific Customer Details</h3>
            <input 
              type="text" 
              value={searchCustomerId} 
              onChange={(e) => setSearchCustomerId(e.target.value)}
              placeholder="Enter Customer ID"
              style={{marginRight: '10px'}}
            />
            <button onClick={handleSearchCustomer}>Search Customer</button>
            {selectedCustomerId && <CustomerDetails customerId={selectedCustomerId} onBookingCancelled={refreshCustomerDetails} />}
          </section>
        </div>
        
        <div style={{ flex: 2, border: '1px solid #ccc', padding: '15px' }}>
          <h2>Flight & Booking Management</h2>
          <FlightList onBookingListChanged={triggerBookingsRefresh} /> {/* Pass new prop */}
          <section style={{ marginTop: '20px', padding: '15px', border: '1px solid #eee' }}>
            <SwapSeatsForm onSeatsSwapped={handleSeatsSwapped} refreshTrigger={bookingsRefreshKey} /> 
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;
