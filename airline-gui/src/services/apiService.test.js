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

const queueSuccess = (body) => {
  globalThis.fetch.mockResolvedValueOnce(makeResponse({ body }));
};

const queueHttpError = ({ status, body, jsonReject = false }) => {
  globalThis.fetch.mockResolvedValueOnce(makeResponse({ ok: false, status, body, jsonReject }));
};

const expectSimpleSuccessAndHttpError = async ({ action, successBody, failStatus }) => {
  queueSuccess(successBody);
  await expect(action()).resolves.toEqual(successBody);

  queueHttpError({ status: failStatus });
  await expect(action()).rejects.toThrow(`HTTP error! status: ${failStatus}`);
};

const expectDetailedSuccessAndErrorPaths = async ({ action, successBody, failStatus, failMessage }) => {
  queueSuccess(successBody);
  await expect(action()).resolves.toEqual(successBody);

  queueHttpError({ status: failStatus, body: { error: failMessage } });
  await expect(action()).rejects.toThrow(`HTTP error! status: ${failStatus} - ${failMessage}`);

  queueHttpError({ status: 500, jsonReject: true });
  await expect(action()).rejects.toThrow('HTTP error! status: 500 - Unknown error occurred');
};

const loadModuleWithBaseUrl = async ({ baseUrl, locationOrigin }) => {
  vi.resetModules();
  vi.stubEnv('VITE_API_BASE_URL', baseUrl);

  if (typeof locationOrigin === 'string') {
    vi.stubGlobal('location', { origin: locationOrigin });
  }

  const fetchMock = vi.fn().mockResolvedValue(makeResponse({ body: [{ flightNumber: 'CFG' }] }));
  globalThis.fetch = fetchMock;

  const apiModule = await import('./apiService');
  await expect(apiModule.fetchAirplanes()).resolves.toEqual([{ flightNumber: 'CFG' }]);

  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  return fetchMock;
};

describe('apiService', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = vi.fn();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it.each([
    {
      label: 'fetchAirplanes',
      action: () => fetchAirplanes(),
      successBody: [{ flightNumber: 'FL-1' }],
      failStatus: 503
    },
    {
      label: 'fetchAirplaneDetails',
      action: () => fetchAirplaneDetails('FL-2'),
      successBody: { flightNumber: 'FL-2' },
      failStatus: 404
    },
    {
      label: 'fetchCustomers',
      action: () => fetchCustomers(),
      successBody: [{ personId: 'C1' }],
      failStatus: 502
    }
  ])('$label handles success + status errors', async ({ action, successBody, failStatus }) => {
    await expectSimpleSuccessAndHttpError({
      action,
      successBody,
      failStatus
    });
  });

  it('fetchCustomers surfaces network failures', async () => {
    globalThis.fetch.mockRejectedValueOnce(new Error('network down'));
    await expect(fetchCustomers()).rejects.toThrow('network down');
  });

  it.each([
    {
      label: 'addCustomer',
      action: () => addCustomer({ name: 'Alice' }),
      successBody: { personId: 'C2', name: 'Alice' },
      failStatus: 400,
      failMessage: 'Invalid payload'
    },
    {
      label: 'createBooking',
      action: () => createBooking({ customerId: 'C1' }),
      successBody: { bookingId: 10 },
      failStatus: 409,
      failMessage: 'Seat taken'
    },
    {
      label: 'fetchCustomerDetails',
      action: () => fetchCustomerDetails('C9'),
      successBody: { personId: 'C9' },
      failStatus: 404,
      failMessage: 'Not found'
    },
    {
      label: 'cancelBooking',
      action: () => cancelBooking(77),
      successBody: { message: 'Cancelled' },
      failStatus: 400,
      failMessage: 'Bad request'
    },
    {
      label: 'fetchBookings',
      action: () => fetchBookings(),
      successBody: [{ bookingId: 1 }],
      failStatus: 401,
      failMessage: 'Unauthorized'
    },
    {
      label: 'swapSeats',
      action: () => swapSeats(1, 2),
      successBody: { message: 'Swapped' },
      failStatus: 422,
      failMessage: 'Invalid swap'
    }
  ])('$label handles success + detailed API errors', async ({ action, successBody, failStatus, failMessage }) => {
    await expectDetailedSuccessAndErrorPaths({
      action,
      successBody,
      failStatus,
      failMessage
    });
  });

  it.each([
    {
      label: 'uses configured relative path',
      baseUrl: '/internal-api/',
      expectedTarget: '/internal-api/airplanes'
    },
    {
      label: 'falls back for external absolute URL',
      baseUrl: 'https://api.example.test/api/',
      expectedTarget: '/api/airplanes'
    },
    {
      label: 'falls back for invalid absolute URL',
      baseUrl: 'https://[invalid-url',
      expectedTarget: '/api/airplanes'
    },
    {
      label: 'falls back for disallowed // pathname on same origin',
      baseUrl: 'https://app.local//',
      locationOrigin: 'https://app.local',
      expectedTarget: '/api/airplanes'
    },
    {
      label: 'accepts same-origin absolute URL when origin is null-like',
      baseUrl: 'https://app.local/internal-api',
      locationOrigin: 'null',
      expectedTarget: '/internal-api/airplanes'
    }
  ])('$label', async ({ baseUrl, locationOrigin, expectedTarget }) => {
    const fetchMock = await loadModuleWithBaseUrl({ baseUrl, locationOrigin });
    expect(fetchMock).toHaveBeenCalled();
    expect(fetchMock.mock.calls[0][0]).toBe(expectedTarget);
  });

  it('rejects invalid API path inputs via normalizeApiPath guard', () => {
    expect(() => __internal.normalizeApiPath('')).toThrow('Invalid API path');
    expect(() => __internal.normalizeApiPath('airplanes')).toThrow('Invalid API path');
    expect(() => __internal.normalizeApiPath('//airplanes')).toThrow('Invalid API path');
  });

  it('normalizes relative API base paths and rejects falsy values', () => {
    expect(__internal.normalizeRelativeBasePath(null)).toBe('');
    expect(__internal.normalizeRelativeBasePath('internal-api/')).toBe('/internal-api');
  });

  it('rejects unsafe path segment inputs', () => {
    expect(() => __internal.encodePathSegment('', 'booking id')).toThrow('Invalid booking id: value is required');
    expect(() => __internal.encodePathSegment('a/b', 'booking id')).toThrow(
      'Invalid booking id: path separators are not allowed'
    );
    expect(() => __internal.encodePathSegment(String.raw`a\b`, 'booking id')).toThrow(
      'Invalid booking id: path separators are not allowed'
    );
  });
});
