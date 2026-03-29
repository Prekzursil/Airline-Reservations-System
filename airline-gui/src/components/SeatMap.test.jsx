import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SeatMap from './SeatMap';
import {
  cancelBooking,
  createBooking,
  fetchCustomers
} from '../services/apiService';

vi.mock('../services/apiService', () => ({
  createBooking: vi.fn(),
  fetchCustomers: vi.fn(),
  cancelBooking: vi.fn()
}));

vi.mock('react-select', () => ({
  default: ({ id, inputId, options = [], value, onChange, placeholder, isDisabled }) => {
    const controlId = inputId || id || 'react-select';
    return (
      <select
        aria-label={controlId}
        data-testid={controlId}
        disabled={isDisabled}
        value={value?.value ?? ''}
        onChange={(event) => {
          const next = options.find((opt) => String(opt.value) === event.target.value) || null;
          onChange(next);
        }}
      >
        <option value="">{placeholder || 'Select'}</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    );
  }
}));

const baseSeats = [
  {
    seatId: '1A',
    seatClass: 'Business',
    price: 300,
    isBooked: true,
    bookedByCustomerId: 'C-BOOKED',
    bookingId: 501
  },
  {
    seatId: '1B',
    seatClass: 'Economy',
    price: 120,
    isBooked: false
  }
];

describe('SeatMap', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders fallback when no seats are provided', () => {
    render(<SeatMap seats={[]} flightNumber="FL-EMPTY" />);
    expect(screen.getByText('No seat information available for this flight.')).toBeInTheDocument();
  });

  it('shows customer-load error when fetchCustomers fails', async () => {
    fetchCustomers.mockRejectedValue(new Error('customer API down'));

    render(<SeatMap seats={baseSeats} flightNumber="FL-100" />);

    expect(await screen.findByText('Could not load customers for selection.')).toBeInTheDocument();
  });

  it('shows loading customers indicator while customer list is still being fetched', async () => {
    let resolveCustomers;
    const customersPromise = new Promise((resolve) => {
      resolveCustomers = resolve;
    });
    fetchCustomers.mockReturnValue(customersPromise);

    render(<SeatMap seats={baseSeats} flightNumber="FL-150" />);

    fireEvent.click(await screen.findByText('1B'));
    expect(screen.getByText('Loading customers...')).toBeInTheDocument();

    resolveCustomers([{ personId: 'C1', name: 'Alice' }]);
    await waitFor(() => {
      expect(screen.getByTestId('customerSelectBooking')).toBeInTheDocument();
    });
  });

  it('handles booked-seat info and inline cancel-booking confirmation branches', async () => {
    const onBookingSuccess = vi.fn();
    fetchCustomers.mockResolvedValue([{ personId: 'C1', name: 'Alice' }]);

    render(<SeatMap seats={baseSeats} flightNumber="FL-200" onBookingSuccess={onBookingSuccess} />);

    fireEvent.click(await screen.findByText('1A'));
    expect(screen.getByText('Seat 1A: Booked by Customer ID C-BOOKED.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Cancel booking 501' }));
    expect(screen.getByText('Confirm cancellation for booking 501.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Keep booking 501' }));
    expect(cancelBooking).not.toHaveBeenCalled();
    expect(screen.getByText('Cancellation kept.')).toBeInTheDocument();

    cancelBooking.mockResolvedValueOnce({ message: 'Booking 501 cancelled' });
    fireEvent.click(screen.getByRole('button', { name: 'Cancel booking 501' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm cancellation for booking 501' }));

    expect(await screen.findByText('Booking 501 cancelled')).toBeInTheDocument();
    expect(cancelBooking).toHaveBeenCalledWith(501);
    expect(onBookingSuccess).toHaveBeenCalledWith('FL-200');

    cancelBooking.mockResolvedValueOnce({});
    fireEvent.click(screen.getByRole('button', { name: 'Cancel booking 501' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm cancellation for booking 501' }));

    expect(
      await screen.findByText('Booking 501 cancellation processed.')
    ).toBeInTheDocument();

    cancelBooking.mockRejectedValueOnce(new Error('cancel failed'));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel booking 501' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirm cancellation for booking 501' }));

    expect(await screen.findByText('Failed to cancel booking 501: cancel failed')).toBeInTheDocument();
  });

  it('handles available-seat booking validation, success, and failure branches', async () => {
    const onBookingSuccess = vi.fn();

    fetchCustomers.mockResolvedValue([{ personId: 'C1', name: 'Alice' }]);
    createBooking
      .mockResolvedValueOnce({ bookingId: 700, seatId: '1B', customerId: 'C1' })
      .mockRejectedValueOnce(new Error('insufficient funds'));

    render(<SeatMap seats={baseSeats} flightNumber="FL-300" onBookingSuccess={onBookingSuccess} />);

    fireEvent.click(await screen.findByText('1B'));
    expect(screen.getByText('Selected seat: 1B (Economy, Price: $120)')).toBeInTheDocument();

    expect(screen.getByRole('button', { name: 'Confirm Booking for 1B' })).toBeDisabled();

    fireEvent.change(screen.getByTestId('customerSelectBooking'), { target: { value: 'C1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Booking for 1B' }));

    expect(
      await screen.findByText('Booking successful! ID: 700. Seat: 1B for Customer: C1')
    ).toBeInTheDocument();
    expect(onBookingSuccess).toHaveBeenCalledWith('FL-300');

    fireEvent.click(screen.getByText('1B'));
    fireEvent.change(screen.getByTestId('customerSelectBooking'), { target: { value: 'C1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Booking for 1B' }));

    await waitFor(() => {
      expect(screen.getByText('Booking failed: insufficient funds')).toBeInTheDocument();
    });
  });

  it('supports keyboard seat selection for accessibility', async () => {
    fetchCustomers.mockResolvedValue([{ personId: 'C1', name: 'Alice' }]);

    render(<SeatMap seats={baseSeats} flightNumber="FL-310" />);

    const seatButton = await screen.findByRole('button', { name: 'Seat 1B' });
    expect(seatButton).toHaveAttribute('aria-pressed', 'false');
    seatButton.focus();
    expect(seatButton).toHaveFocus();

    await userEvent.keyboard('{Enter}');
    expect(screen.getByText('Selected seat: 1B (Economy, Price: $120)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Seat 1B' })).toHaveAttribute('aria-pressed', 'true');

    await userEvent.keyboard(' ');
    expect(screen.getByText('Selected seat: 1B (Economy, Price: $120)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Seat 1B' })).toHaveAttribute('aria-pressed', 'true');
  });

});
