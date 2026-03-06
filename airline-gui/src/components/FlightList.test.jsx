import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import FlightList from './FlightList';
import { fetchAirplaneDetails, fetchAirplanes } from '../services/apiService';

vi.mock('../services/apiService', () => ({
  fetchAirplanes: vi.fn(),
  fetchAirplaneDetails: vi.fn()
}));

vi.mock('./SeatMap', () => ({
  default: ({ flightNumber, onBookingSuccess }) => (
    <div data-testid="mock-seat-map">
      <span>Mock SeatMap for {flightNumber}</span>
      <button onClick={() => onBookingSuccess?.(flightNumber)}>Mock SeatMap Booking Success</button>
    </div>
  )
}));

describe('FlightList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('loads flights, renders details on select, and toggles details off on repeated click', async () => {
    fetchAirplanes.mockResolvedValue([
      { flightNumber: 'FL-100', capacity: 120, bookedSeatsCount: 10 },
      { flightNumber: 'FL-200', capacity: 80, bookedSeatsCount: 5 }
    ]);
    fetchAirplaneDetails.mockResolvedValue({ seats: [{ seatId: '1A' }] });

    render(<FlightList />);

    const flightOneButton = await screen.findByRole('button', { name: /FL-100/i });
    expect(flightOneButton).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('button', { name: /FL-200/i })).toBeInTheDocument();

    fireEvent.click(flightOneButton);
    expect(await screen.findByText('Details for Flight: FL-100')).toBeInTheDocument();
    expect(screen.getByText('Mock SeatMap for FL-100')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /FL-100/i })).toHaveAttribute('aria-expanded', 'true');

    fireEvent.click(screen.getByRole('button', { name: /FL-100/i }));
    await waitFor(() => {
      expect(screen.queryByText('Details for Flight: FL-100')).not.toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /FL-100/i })).toHaveAttribute('aria-expanded', 'false');
  });

  it('shows airplane-load error when fetchAirplanes fails', async () => {
    fetchAirplanes.mockRejectedValue(new Error('airplanes unavailable'));

    render(<FlightList />);

    expect(
      await screen.findByText('Error: Failed to load airplanes. Ensure the C++ API server is running.')
    ).toBeInTheDocument();
  });

  it('shows details-load error when fetching flight details fails', async () => {
    fetchAirplanes.mockResolvedValue([{ flightNumber: 'FL-300', capacity: 90, bookedSeatsCount: 9 }]);
    fetchAirplaneDetails.mockRejectedValue(new Error('details unavailable'));

    render(<FlightList />);

    fireEvent.click(await screen.findByRole('button', { name: /FL-300/i }));
    expect(await screen.findByText('Error: Failed to load details for flight FL-300.')).toBeInTheDocument();
  });

  it('executes booking refresh callbacks on success path', async () => {
    const onBookingListChanged = vi.fn();

    fetchAirplanes
      .mockResolvedValueOnce([{ flightNumber: 'FL-300', capacity: 90, bookedSeatsCount: 9 }])
      .mockResolvedValueOnce([{ flightNumber: 'FL-300', capacity: 90, bookedSeatsCount: 10 }]);

    fetchAirplaneDetails
      .mockResolvedValueOnce({ seats: [{ seatId: '2A' }] })
      .mockResolvedValueOnce({ seats: [{ seatId: '2A' }] });

    render(<FlightList onBookingListChanged={onBookingListChanged} />);

    const flightButton = await screen.findByRole('button', { name: /FL-300/i });
    fireEvent.click(flightButton);
    expect(await screen.findByText('Details for Flight: FL-300')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Mock SeatMap Booking Success' }));

    await waitFor(() => {
      expect(onBookingListChanged).toHaveBeenCalledTimes(1);
      expect(fetchAirplanes).toHaveBeenCalledTimes(2);
      expect(fetchAirplaneDetails).toHaveBeenCalledTimes(2);
    });
  });

  it('shows refresh error when airplane list refresh fails after booking success callback', async () => {
    fetchAirplanes
      .mockResolvedValueOnce([{ flightNumber: 'FL-400', capacity: 100, bookedSeatsCount: 20 }])
      .mockRejectedValueOnce(new Error('refresh failed'));
    fetchAirplaneDetails.mockResolvedValue({ seats: [{ seatId: '3A' }] });

    render(<FlightList />);

    fireEvent.click(await screen.findByRole('button', { name: /FL-400/i }));
    expect(await screen.findByText('Details for Flight: FL-400')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Mock SeatMap Booking Success' }));

    expect(await screen.findByText('Error: Failed to refresh airplane list after booking.')).toBeInTheDocument();
  });
});
