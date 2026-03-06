import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import SwapSeatsForm from './SwapSeatsForm';
import { fetchBookings, swapSeats } from '../services/apiService';

vi.mock('../services/apiService', () => ({
  fetchBookings: vi.fn(),
  swapSeats: vi.fn()
}));

vi.mock('react-select', () => ({
  default: ({ id, inputId, options = [], value, onChange, placeholder, isDisabled }) => {
    const controlId = inputId || id || 'react-select';
    return (
      <div>
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
        <button
          type="button"
          data-testid={`${controlId}-force-1`}
          onClick={() => onChange({ value: 1, label: 'Forced booking 1' })}
        >
          Force 1
        </button>
      </div>
    );
  }
}));

const bookings = [
  { bookingId: 1, customerId: 'C1', flightNumber: 'FL-1', seatId: '1A', status: 'Confirmed' },
  { bookingId: 2, customerId: 'C2', flightNumber: 'FL-1', seatId: '1B', status: 'Confirmed' },
  { bookingId: 3, customerId: 'C3', flightNumber: 'FL-2', seatId: '2C', status: 'CANCELLED' }
];

describe('SwapSeatsForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows loading/error/empty states when bookings cannot be loaded', async () => {
    fetchBookings.mockRejectedValue(new Error('downstream unavailable'));

    render(<SwapSeatsForm refreshTrigger={0} />);

    expect(screen.getByText('Loading bookings...')).toBeInTheDocument();
    expect(await screen.findByText('Could not load bookings.')).toBeInTheDocument();
    expect(screen.queryByText('No confirmed bookings available to swap.')).not.toBeInTheDocument();
  });

  it('treats null bookings payload as empty list', async () => {
    fetchBookings.mockResolvedValue(null);

    render(<SwapSeatsForm refreshTrigger={5} />);

    await waitFor(() => {
      expect(fetchBookings).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByText('No confirmed bookings available to swap.')).toBeInTheDocument();
  });

  it('validates missing selections and applies distinct-option filtering', async () => {
    fetchBookings.mockResolvedValue(bookings);

    render(<SwapSeatsForm refreshTrigger={1} />);

    await waitFor(() => {
      expect(fetchBookings).toHaveBeenCalledTimes(1);
    });
    const form = screen.getByRole('button', { name: 'Swap Selected Seats' }).closest('form');

    fireEvent.submit(form);
    expect(screen.getByText('Please select both bookings.')).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('booking1SelectSwap'), { target: { value: '1' } });
    expect(screen.queryByRole('option', { name: /ID: 1 \\(Cust: C1, Flight: FL-1, Seat: 1A\\)/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('booking2SelectSwap-force-1'));
    fireEvent.submit(form);
    expect(screen.getByText('Booking IDs must be different.')).toBeInTheDocument();
  });

  it('submits successful swap and then handles swap failure', async () => {
    const onSeatsSwapped = vi.fn();

    fetchBookings
      .mockResolvedValueOnce(bookings)
      .mockResolvedValueOnce(bookings);
    swapSeats
      .mockResolvedValueOnce({})
      .mockRejectedValueOnce(new Error('swap blocked'));

    const { rerender } = render(<SwapSeatsForm onSeatsSwapped={onSeatsSwapped} refreshTrigger={2} />);

    await waitFor(() => {
      expect(fetchBookings).toHaveBeenCalledTimes(1);
    });

    fireEvent.change(screen.getByTestId('booking1SelectSwap'), { target: { value: '1' } });
    fireEvent.change(screen.getByTestId('booking2SelectSwap'), { target: { value: '2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Swap Selected Seats' }));

    expect(await screen.findByText('Seat swap processed.')).toBeInTheDocument();
    expect(swapSeats).toHaveBeenCalledWith(1, 2);
    expect(onSeatsSwapped).toHaveBeenCalledTimes(1);

    rerender(<SwapSeatsForm onSeatsSwapped={onSeatsSwapped} refreshTrigger={3} />);
    await waitFor(() => expect(fetchBookings).toHaveBeenCalledTimes(2));

    fireEvent.change(screen.getByTestId('booking1SelectSwap'), { target: { value: '1' } });
    fireEvent.change(screen.getByTestId('booking2SelectSwap'), { target: { value: '2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Swap Selected Seats' }));

    await waitFor(() => {
      expect(screen.getByText('Failed to swap seats: swap blocked')).toBeInTheDocument();
    });
  });
});
