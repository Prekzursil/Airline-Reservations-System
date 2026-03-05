import {
  __internal,
  addCustomer,
  cancelBooking,
  createBooking,
  fetchAirplaneDetails,
  fetchAirplanes,
  fetchBookings,
  fetchCustomerDetails,
  fetchCustomers,
  swapSeats
} from './apiService';

const makeResponse = ({ ok = true, status = 200, body = {}, jsonReject = false } = {}) => ({
  ok,
  status,
  json: jsonReject
    ? vi.fn().mockRejectedValue(new Error('json parse failed'))
    : vi.fn().mockResolvedValue(body)
});

describe('apiService', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = vi.fn();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetchAirplanes success and failure', async () => {
    globalThis.fetch.mockResolvedValueOnce(makeResponse({ body: [{ flightNumber: 'FL-1' }] }));
    await expect(fetchAirplanes()).resolves.toEqual([{ flightNumber: 'FL-1' }]);

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 503 }));
    await expect(fetchAirplanes()).rejects.toThrow('HTTP error! status: 503');
  });

  it('fetchAirplaneDetails success and failure', async () => {
    globalThis.fetch.mockResolvedValueOnce(makeResponse({ body: { flightNumber: 'FL-2' } }));
    await expect(fetchAirplaneDetails('FL-2')).resolves.toEqual({ flightNumber: 'FL-2' });

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 404 }));
    await expect(fetchAirplaneDetails('FL-2')).rejects.toThrow('HTTP error! status: 404');
  });

  it('fetchCustomers success and failure', async () => {
    globalThis.fetch.mockResolvedValueOnce(makeResponse({ body: [{ personId: 'C1' }] }));
    await expect(fetchCustomers()).resolves.toEqual([{ personId: 'C1' }]);

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 502 }));
    await expect(fetchCustomers()).rejects.toThrow('HTTP error! status: 502');

    globalThis.fetch.mockRejectedValueOnce(new Error('network down'));
    await expect(fetchCustomers()).rejects.toThrow('network down');
  });

  it('addCustomer handles success, API errors, and fallback error-body parsing', async () => {
    globalThis.fetch.mockResolvedValueOnce(makeResponse({ body: { personId: 'C2', name: 'Alice' } }));
    await expect(addCustomer({ name: 'Alice' })).resolves.toEqual({ personId: 'C2', name: 'Alice' });

    globalThis.fetch.mockResolvedValueOnce(
      makeResponse({ ok: false, status: 400, body: { error: 'Invalid payload' } })
    );
    await expect(addCustomer({})).rejects.toThrow('HTTP error! status: 400 - Invalid payload');

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 500, jsonReject: true }));
    await expect(addCustomer({})).rejects.toThrow('HTTP error! status: 500 - Unknown error occurred');
  });

  it('createBooking handles success and both error-body paths', async () => {
    globalThis.fetch.mockResolvedValueOnce(makeResponse({ body: { bookingId: 10 } }));
    await expect(createBooking({ customerId: 'C1' })).resolves.toEqual({ bookingId: 10 });

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 409, body: { error: 'Seat taken' } }));
    await expect(createBooking({})).rejects.toThrow('HTTP error! status: 409 - Seat taken');

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 500, jsonReject: true }));
    await expect(createBooking({})).rejects.toThrow('HTTP error! status: 500 - Unknown error occurred');
  });

  it('fetchCustomerDetails handles success and both error-body paths', async () => {
    globalThis.fetch.mockResolvedValueOnce(makeResponse({ body: { personId: 'C9' } }));
    await expect(fetchCustomerDetails('C9')).resolves.toEqual({ personId: 'C9' });

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 404, body: { error: 'Not found' } }));
    await expect(fetchCustomerDetails('C9')).rejects.toThrow('HTTP error! status: 404 - Not found');

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 500, jsonReject: true }));
    await expect(fetchCustomerDetails('C9')).rejects.toThrow('HTTP error! status: 500 - Unknown error occurred');
  });

  it('cancelBooking handles success and both error-body paths', async () => {
    globalThis.fetch.mockResolvedValueOnce(makeResponse({ body: { message: 'Cancelled' } }));
    await expect(cancelBooking(77)).resolves.toEqual({ message: 'Cancelled' });

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 400, body: { error: 'Bad request' } }));
    await expect(cancelBooking(77)).rejects.toThrow('HTTP error! status: 400 - Bad request');

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 500, jsonReject: true }));
    await expect(cancelBooking(77)).rejects.toThrow('HTTP error! status: 500 - Unknown error occurred');
  });

  it('fetchBookings handles success and both error-body paths', async () => {
    globalThis.fetch.mockResolvedValueOnce(makeResponse({ body: [{ bookingId: 1 }] }));
    await expect(fetchBookings()).resolves.toEqual([{ bookingId: 1 }]);

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 401, body: { error: 'Unauthorized' } }));
    await expect(fetchBookings()).rejects.toThrow('HTTP error! status: 401 - Unauthorized');

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 500, jsonReject: true }));
    await expect(fetchBookings()).rejects.toThrow('HTTP error! status: 500 - Unknown error occurred');
  });

  it('swapSeats handles success and both error-body paths', async () => {
    globalThis.fetch.mockResolvedValueOnce(makeResponse({ body: { message: 'Swapped' } }));
    await expect(swapSeats(1, 2)).resolves.toEqual({ message: 'Swapped' });

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 422, body: { error: 'Invalid swap' } }));
    await expect(swapSeats(1, 2)).rejects.toThrow('HTTP error! status: 422 - Invalid swap');

    globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status: 500, jsonReject: true }));
    await expect(swapSeats(1, 2)).rejects.toThrow('HTTP error! status: 500 - Unknown error occurred');
  });

  it('uses configured VITE_API_BASE_URL when provided as a relative path', async () => {
    vi.resetModules();
    vi.stubEnv('VITE_API_BASE_URL', '/internal-api/');

    const fetchMock = vi.fn().mockResolvedValue(makeResponse({ body: [{ flightNumber: 'CFG-1' }] }));
    globalThis.fetch = fetchMock;

    const apiModule = await import('./apiService');
    await expect(apiModule.fetchAirplanes()).resolves.toEqual([{ flightNumber: 'CFG-1' }]);

    expect(fetchMock).toHaveBeenCalled();
    expect(fetchMock.mock.calls[0][0]).toBe('/internal-api/airplanes');

    vi.unstubAllEnvs();
  });

  it('falls back to default API path when VITE_API_BASE_URL is an external absolute URL', async () => {
    vi.resetModules();
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/api/');

    const fetchMock = vi.fn().mockResolvedValue(makeResponse({ body: [{ flightNumber: 'CFG-2' }] }));
    globalThis.fetch = fetchMock;

    const apiModule = await import('./apiService');
    await expect(apiModule.fetchAirplanes()).resolves.toEqual([{ flightNumber: 'CFG-2' }]);

    expect(fetchMock).toHaveBeenCalled();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/airplanes');

    vi.unstubAllEnvs();
  });

  it('falls back to default API path when configured absolute URL is invalid', async () => {
    vi.resetModules();
    vi.stubEnv('VITE_API_BASE_URL', 'https://[invalid-url');

    const fetchMock = vi.fn().mockResolvedValue(makeResponse({ body: [{ flightNumber: 'CFG-3' }] }));
    globalThis.fetch = fetchMock;

    const apiModule = await import('./apiService');
    await expect(apiModule.fetchAirplanes()).resolves.toEqual([{ flightNumber: 'CFG-3' }]);

    expect(fetchMock).toHaveBeenCalled();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/airplanes');

    vi.unstubAllEnvs();
  });

  it('falls back to default API path when same-origin absolute URL resolves to disallowed // pathname', async () => {
    vi.resetModules();
    vi.stubEnv('VITE_API_BASE_URL', 'https://app.local//');
    vi.stubGlobal('location', { origin: 'https://app.local' });

    const fetchMock = vi.fn().mockResolvedValue(makeResponse({ body: [{ flightNumber: 'CFG-4' }] }));
    globalThis.fetch = fetchMock;

    const apiModule = await import('./apiService');
    await expect(apiModule.fetchAirplanes()).resolves.toEqual([{ flightNumber: 'CFG-4' }]);

    expect(fetchMock).toHaveBeenCalled();
    expect(fetchMock.mock.calls[0][0]).toBe('/api/airplanes');

    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('accepts absolute URL path when location.origin is null-like', async () => {
    vi.resetModules();
    vi.stubEnv('VITE_API_BASE_URL', 'https://app.local/internal-api');
    vi.stubGlobal('location', { origin: 'null' });

    const fetchMock = vi.fn().mockResolvedValue(makeResponse({ body: [{ flightNumber: 'CFG-5' }] }));
    globalThis.fetch = fetchMock;

    const apiModule = await import('./apiService');
    await expect(apiModule.fetchAirplanes()).resolves.toEqual([{ flightNumber: 'CFG-5' }]);

    expect(fetchMock).toHaveBeenCalled();
    expect(fetchMock.mock.calls[0][0]).toBe('/internal-api/airplanes');

    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('rejects invalid API path inputs via normalizeApiPath guard', () => {
    expect(() => __internal.normalizeApiPath('airplanes')).toThrow('Invalid API path');
    expect(() => __internal.normalizeApiPath('//airplanes')).toThrow('Invalid API path');
  });

  it('rejects unsafe path segment inputs', () => {
    expect(() => __internal.encodePathSegment('', 'booking id')).toThrow('Invalid booking id: value is required');
    expect(() => __internal.encodePathSegment('a/b', 'booking id')).toThrow(
      'Invalid booking id: path separators are not allowed'
    );
    expect(() => __internal.encodePathSegment('a\\b', 'booking id')).toThrow(
      'Invalid booking id: path separators are not allowed'
    );
  });
});
