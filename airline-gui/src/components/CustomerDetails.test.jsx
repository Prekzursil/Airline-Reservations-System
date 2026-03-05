import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import CustomerDetails from './CustomerDetails';
import { cancelBooking, fetchCustomerDetails } from '../services/apiService';

vi.mock('../services/apiService', () => ({
  fetchCustomerDetails: vi.fn(),
  cancelBooking: vi.fn()
}));

describe('CustomerDetails', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(globalThis, 'confirm').mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders no-id message when customerId is empty', () => {
    render(<CustomerDetails customerId="" />);
    expect(screen.getByText('Select or enter a customer ID to view details.')).toBeInTheDocument();
    expect(fetchCustomerDetails).not.toHaveBeenCalled();
  });

  it('loads customer details successfully and handles no-bookings state', async () => {
    const deferred = {};
    deferred.promise = new Promise((resolve) => {
      deferred.resolve = resolve;
    });
    fetchCustomerDetails.mockReturnValueOnce(deferred.promise);

    render(<CustomerDetails customerId="C1" />);

    expect(screen.getByText('Loading customer details...')).toBeInTheDocument();

    deferred.resolve({
      personId: 'C1',
      name: 'Alice',
      age: 28,
      money: 350,
      bookings: []
    });

    expect(await screen.findByText('Customer Details: Alice (ID: C1)')).toBeInTheDocument();
    expect(screen.getByText('No bookings found for this customer.')).toBeInTheDocument();
  });

  it('loads bookings and hides cancel button for cancelled entries', async () => {
    fetchCustomerDetails.mockResolvedValue({
      personId: 'C2',
      name: 'Bob',
      age: 44,
      money: 120,
      bookings: [
        { bookingId: 10, flightNumber: 'FL-100', seatId: '1A', status: 'Confirmed' },
        { bookingId: 11, flightNumber: 'FL-200', seatId: '2B', status: 'CANCELLED' }
      ]
    });

    render(<CustomerDetails customerId="C2" />);

    expect(await screen.findByText('Customer Details: Bob (ID: C2)')).toBeInTheDocument();
    expect(screen.getByText('ID: 10, Flight: FL-100, Seat: 1A, Status: Confirmed')).toBeInTheDocument();
    expect(screen.getByText('ID: 11, Flight: FL-200, Seat: 2B, Status: CANCELLED')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Cancel Booking' })).toHaveLength(1);
  });

  it('shows load error when customer details fetch fails', async () => {
    fetchCustomerDetails.mockRejectedValue(new Error('Not Found'));

    render(<CustomerDetails customerId="C404" />);

    expect(
      await screen.findByText('Failed to load details for customer C404: Not Found')
    ).toBeInTheDocument();
  });

  it('does not cancel booking when confirmation is rejected', async () => {
    globalThis.confirm.mockReturnValue(false);
    fetchCustomerDetails.mockResolvedValue({
      personId: 'C3',
      name: 'Chris',
      age: 33,
      money: 220,
      bookings: [{ bookingId: 21, flightNumber: 'FL-300', seatId: '3A', status: 'Confirmed' }]
    });

    render(<CustomerDetails customerId="C3" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Cancel Booking' }));

    expect(cancelBooking).not.toHaveBeenCalled();
    expect(screen.queryByText(/Cancelling booking 21.../)).not.toBeInTheDocument();
  });

  it('cancels booking successfully and triggers refresh callback', async () => {
    const onBookingCancelled = vi.fn();
    fetchCustomerDetails.mockResolvedValue({
      personId: 'C4',
      name: 'Dana',
      age: 37,
      money: 500,
      bookings: [{ bookingId: 31, flightNumber: 'FL-400', seatId: '4C', status: 'Confirmed' }]
    });
    cancelBooking.mockResolvedValue({ message: 'Booking 31 cancelled' });

    render(<CustomerDetails customerId="C4" onBookingCancelled={onBookingCancelled} />);

    fireEvent.click(await screen.findByRole('button', { name: 'Cancel Booking' }));

    expect(await screen.findByText('Booking 31 cancelled')).toBeInTheDocument();
    expect(cancelBooking).toHaveBeenCalledWith(31);
    expect(onBookingCancelled).toHaveBeenCalledWith('C4');
  });

  it('uses cancellation fallback message when API omits message field', async () => {
    fetchCustomerDetails.mockResolvedValue({
      personId: 'C4B',
      name: 'Dana B',
      age: 37,
      money: 500,
      bookings: [{ bookingId: 32, flightNumber: 'FL-401', seatId: '4D', status: 'Confirmed' }]
    });
    cancelBooking.mockResolvedValue({});

    render(<CustomerDetails customerId="C4B" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Cancel Booking' }));

    expect(await screen.findByText('Booking 32 cancellation processed.')).toBeInTheDocument();
  });

  it('shows cancellation error when cancelBooking fails', async () => {
    fetchCustomerDetails.mockResolvedValue({
      personId: 'C5',
      name: 'Eve',
      age: 30,
      money: 400,
      bookings: [{ bookingId: 41, flightNumber: 'FL-500', seatId: '5D', status: 'Confirmed' }]
    });
    cancelBooking.mockRejectedValue(new Error('Cancellation blocked'));

    render(<CustomerDetails customerId="C5" />);

    fireEvent.click(await screen.findByRole('button', { name: 'Cancel Booking' }));

    await waitFor(() => {
      expect(screen.getByText('Failed to cancel booking 41: Cancellation blocked')).toBeInTheDocument();
    });
  });
});
