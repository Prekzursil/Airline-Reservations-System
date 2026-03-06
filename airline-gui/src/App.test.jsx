import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from './App';
import { fetchCustomers } from './services/apiService';

vi.mock('./services/apiService', () => ({
  fetchCustomers: vi.fn()
}));

vi.mock('./components/CustomerForm', () => ({
  default: ({ onCustomerAdded }) => (
    <div>
      <button onClick={() => onCustomerAdded?.({ personId: 'NEW-1', name: 'New Customer' })}>
        Mock Add Customer
      </button>
    </div>
  )
}));

vi.mock('./components/CustomerDetails', () => ({
  default: ({ customerId, onBookingCancelled, refreshTrigger }) => (
    <div data-testid="mock-customer-details">
      <span>Mock CustomerDetails for {customerId}</span>
      <span data-testid="customer-details-refresh-trigger">{String(refreshTrigger)}</span>
      <button onClick={() => onBookingCancelled?.(customerId)}>Mock Cancel Booking</button>
    </div>
  )
}));

vi.mock('./components/FlightList', () => ({
  default: ({ onBookingListChanged }) => (
    <div>
      <button onClick={() => onBookingListChanged?.()}>Mock Booking List Changed</button>
    </div>
  )
}));

vi.mock('./components/SwapSeatsForm', () => ({
  default: ({ onSeatsSwapped, refreshTrigger }) => (
    <div>
      <span data-testid="refresh-trigger">{String(refreshTrigger)}</span>
      <button onClick={() => onSeatsSwapped?.()}>Mock Swap Seats</button>
    </div>
  )
}));

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(globalThis, 'alert').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads customers on startup and supports selecting/searching customers', async () => {
    fetchCustomers.mockResolvedValue([
      { personId: 'C1', name: 'Alice' },
      { personId: 'C2', name: 'Bob' }
    ]);

    render(<App />);

    expect(await screen.findByText('All Customers:')).toBeInTheDocument();
    const aliceButton = screen.getByRole('button', { name: 'Alice (ID: C1)' });
    const bobButton = screen.getByRole('button', { name: 'Bob (ID: C2)' });
    expect(aliceButton).toBeInTheDocument();
    expect(bobButton).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Refresh Customer List' })).toBeInTheDocument();
    expect(aliceButton).toHaveAttribute('aria-pressed', 'false');
    expect(bobButton).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(aliceButton);
    expect(screen.getByDisplayValue('C1')).toBeInTheDocument();
    expect(screen.getByText('Mock CustomerDetails for C1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Alice (ID: C1)' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Bob (ID: C2)' })).toHaveAttribute('aria-pressed', 'false');

    const searchInput = screen.getByPlaceholderText('Enter Customer ID');
    fireEvent.change(searchInput, { target: { value: 'C2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Search Customer' }));

    expect(screen.getByText('Mock CustomerDetails for C2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Alice (ID: C1)' })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button', { name: 'Bob (ID: C2)' })).toHaveAttribute('aria-pressed', 'true');
    expect(fetchCustomers).toHaveBeenCalledTimes(1);
  });

  it('shows load error and then supports manual refresh to an empty customer state', async () => {
    fetchCustomers
      .mockRejectedValueOnce(new Error('API down'))
      .mockResolvedValueOnce([]);

    render(<App />);

    expect(
      await screen.findByText('Failed to load customers. Ensure API server is running.')
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Show Customer List' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Show Customer List' }));

    expect(await screen.findByText('No customers found.')).toBeInTheDocument();
    expect(fetchCustomers).toHaveBeenCalledTimes(2);
  });

  it('refreshes booking-dependent state from customer add, booking callback, and swap actions', async () => {
    fetchCustomers.mockResolvedValue([{ personId: 'C1', name: 'Alice' }]);

    render(<App />);

    await screen.findByText('Alice (ID: C1)');
    expect(screen.getByTestId('refresh-trigger')).toHaveTextContent('0');

    fireEvent.click(screen.getByRole('button', { name: 'Mock Add Customer' }));
    await waitFor(() => expect(fetchCustomers).toHaveBeenCalledTimes(2));
    expect(screen.getByTestId('refresh-trigger')).toHaveTextContent('1');

    fireEvent.click(screen.getByRole('button', { name: 'Mock Booking List Changed' }));
    expect(screen.getByTestId('refresh-trigger')).toHaveTextContent('2');

    fireEvent.click(screen.getByRole('button', { name: 'Mock Swap Seats' }));
    await waitFor(() => expect(fetchCustomers).toHaveBeenCalledTimes(3));
    expect(screen.getByTestId('refresh-trigger')).toHaveTextContent('3');
    expect(globalThis.alert).toHaveBeenCalledWith(
      'Seats swapped. Customer details (if viewing) and booking lists refreshed. You may need to re-select a flight to see seat map updates.'
    );

    fireEvent.click(screen.getByText('Alice (ID: C1)'));
    expect(screen.getByText('Mock CustomerDetails for C1')).toBeInTheDocument();
    expect(screen.getByTestId('customer-details-refresh-trigger')).toHaveTextContent('0');

    fireEvent.click(screen.getByRole('button', { name: 'Mock Cancel Booking' }));
    await waitFor(() => expect(fetchCustomers).toHaveBeenCalledTimes(4));
    await waitFor(() => expect(screen.getByText('Mock CustomerDetails for C1')).toBeInTheDocument());
    expect(screen.getByTestId('customer-details-refresh-trigger')).toHaveTextContent('1');
    expect(screen.getByTestId('refresh-trigger')).toHaveTextContent('4');

    fireEvent.click(screen.getByRole('button', { name: 'Mock Swap Seats' }));
    await waitFor(() => expect(fetchCustomers).toHaveBeenCalledTimes(5));
    await waitFor(() => expect(screen.getByText('Mock CustomerDetails for C1')).toBeInTheDocument());
    expect(screen.getByTestId('customer-details-refresh-trigger')).toHaveTextContent('2');
    expect(screen.getByTestId('refresh-trigger')).toHaveTextContent('5');
  });
});
