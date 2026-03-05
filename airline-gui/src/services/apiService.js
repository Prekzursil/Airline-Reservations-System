const JSON_CONTENT_TYPE = 'application/json';
const UNKNOWN_ERROR = 'Unknown error occurred';
const DEFAULT_API_BASE_PATH = '/api';

const trimTrailingSlash = (value) => {
  let end = value.length;
  while (end > 1 && value[end - 1] === '/') {
    end -= 1;
  }
  return value.slice(0, end);
};

const normalizeRelativeBasePath = (value) => {
  const trimmed = String(value || '').trim();
  if (!trimmed || trimmed.startsWith('//') || trimmed.includes('://')) {
    return '';
  }
  const withLeadingSlash = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
  return trimTrailingSlash(withLeadingSlash);
};

const parseAbsoluteUrl = (value) => {
  try {
    return new URL(value);
  } catch {
    return null;
  }
};

const getCurrentOrigin = () => {
  const origin = globalThis.location?.origin;
  if (typeof origin !== 'string' || origin === '' || origin === 'null') {
    return '';
  }
  return origin;
};

const buildDefaultApiBasePath = () => DEFAULT_API_BASE_PATH;

const resolveApiBasePath = () => {
  const configured = String(import.meta?.env?.VITE_API_BASE_URL || '').trim();
  if (!configured) {
    return buildDefaultApiBasePath();
  }

  const relativePath = normalizeRelativeBasePath(configured);
  if (relativePath) {
    return relativePath;
  }

  const parsed = parseAbsoluteUrl(configured);
  if (!parsed) {
    return buildDefaultApiBasePath();
  }

  const currentOrigin = getCurrentOrigin();
  if (currentOrigin && parsed.origin !== currentOrigin) {
    return buildDefaultApiBasePath();
  }

  const normalizedPathname = normalizeRelativeBasePath(parsed.pathname);
  return normalizedPathname || buildDefaultApiBasePath();
};

const API_BASE_PATH = resolveApiBasePath();

const normalizeApiPath = (path) => {
  const normalizedPath = String(path || '').trim();
  if (!normalizedPath.startsWith('/') || normalizedPath.startsWith('//')) {
    throw new Error(`Invalid API path: ${path}`);
  }
  return normalizedPath;
};

const buildRequestTarget = (path) => `${API_BASE_PATH}${normalizeApiPath(path)}`;

const jsonHeaders = { 'Content-Type': JSON_CONTENT_TYPE };

const parseErrorMessage = async (response) => {
  try {
    const errorBody = await response.json();
    const message = errorBody?.error;
    if (typeof message === 'string' && message.trim()) {
      return message;
    }
  } catch {
    // Keep fallback message if response body is not JSON.
  }
  return UNKNOWN_ERROR;
};

const requestJson = async (path, options = {}, includeErrorBody = false) => {
  const response = await fetch(buildRequestTarget(path), options);
  if (!response.ok) {
    if (!includeErrorBody) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const message = await parseErrorMessage(response);
    throw new Error(`HTTP error! status: ${response.status} - ${message}`);
  }
  return response.json();
};

export const fetchAirplanes = async () => requestJson('/airplanes');

export const fetchAirplaneDetails = async (flightNumber) => requestJson(`/airplanes/${flightNumber}`);

export const fetchCustomers = async () => requestJson('/customers');

export const addCustomer = async (customerData) =>
  requestJson(
    '/customers',
    {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify(customerData)
    },
    true
  );

export const createBooking = async (bookingData) =>
  requestJson(
    '/bookings',
    {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify(bookingData)
    },
    true
  );

export const fetchCustomerDetails = async (customerId) => requestJson(`/customers/${customerId}`, {}, true);

export const cancelBooking = async (bookingId) =>
  requestJson(
    `/bookings/${bookingId}`,
    {
      method: 'DELETE'
    },
    true
  );

export const fetchBookings = async () => requestJson('/bookings', {}, true);

export const swapSeats = async (bookingId1, bookingId2) =>
  requestJson(
    '/bookings/swap',
    {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ bookingId1, bookingId2 })
    },
    true
  );
