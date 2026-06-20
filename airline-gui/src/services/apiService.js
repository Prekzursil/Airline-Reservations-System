const JSON_CONTENT_TYPE = 'application/json';
const UNKNOWN_ERROR = 'Unknown error occurred';
const DEFAULT_API_BASE_PATH = '/api';

/**
 * Removes redundant trailing slashes from an API base path.
 *
 * @param {string} value The raw path to normalize.
 * @returns {string} The normalized path without trailing slashes.
 */
const trimTrailingSlash = (value) => {
  let end = value.length;
  while (end > 1 && value[end - 1] === '/') {
    end -= 1;
  }
  return value.slice(0, end);
};

/**
 * Normalizes a relative API base path and rejects protocol-prefixed inputs.
 *
 * @param {string} value The configured base path.
 * @returns {string} The normalized relative API path or an empty string.
 */
const normalizeRelativeBasePath = (value) => {
  const trimmed = String(value || '').trim();
  if (!trimmed || trimmed.startsWith('//') || trimmed.includes('://')) {
    return '';
  }
  const withLeadingSlash = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
  return trimTrailingSlash(withLeadingSlash);
};

/**
 * Parses an absolute URL string when one is provided.
 *
 * @param {string} value The raw URL candidate.
 * @returns {?URL} The parsed URL when valid, otherwise null.
 */
const parseAbsoluteUrl = (value) => {
  try {
    return new URL(value);
  } catch {
    return null;
  }
};

/**
 * Returns the current browser origin when it is safely available.
 *
 * @returns {string} The current origin or an empty string.
 */
const getCurrentOrigin = () => {
  const origin = globalThis.location?.origin;
  if (typeof origin !== 'string' || origin === '' || origin === 'null') {
    return '';
  }
  return origin;
};

/** Returns the default API base path. */
const buildDefaultApiBasePath = () => DEFAULT_API_BASE_PATH;

/**
 * Resolves the final API base path from the Vite environment.
 *
 * @returns {string} The safe base path used for API requests.
 */
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

/**
 * Validates and normalizes an API path fragment.
 *
 * @param {string} path The API path being requested.
 * @returns {string} The validated path.
 */
const normalizeApiPath = (path) => {
  const normalizedPath = String(path || '').trim();
  if (!normalizedPath.startsWith('/') || normalizedPath.startsWith('//')) {
    throw new Error(`Invalid API path: ${path}`);
  }
  return normalizedPath;
};

/**
 * Builds the final request target for an API path.
 *
 * @param {string} path The request path.
 * @returns {string} The resolved request target.
 */
const buildRequestTarget = (path) => `${API_BASE_PATH}${normalizeApiPath(path)}`;

const jsonHeaders = { 'Content-Type': JSON_CONTENT_TYPE };

/**
 * Encodes a user-supplied path segment after validating it.
 *
 * @param {string|number} value The segment to encode.
 * @param {string} label The label used in validation messages.
 * @returns {string} The encoded segment.
 */
const encodePathSegment = (value, label) => {
  const text = String(value || '').trim();
  if (!text) {
    throw new Error(`Invalid ${label}: value is required`);
  }
  if (text.includes('/') || text.includes('\\')) {
    throw new Error(`Invalid ${label}: path separators are not allowed`);
  }
  return encodeURIComponent(text);
};

export const __internal = {
  normalizeRelativeBasePath,
  normalizeApiPath,
  encodePathSegment,
};

/**
 * Extracts a user-facing error message from an error response body.
 *
 * @param {Response} response The failed fetch response.
 * @returns {Promise<string>} A promise that resolves to a user-facing message.
 */
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

/**
 * Parses a JSON response and raises detailed errors when requested.
 *
 * @param {Response} response The fetch response to parse.
 * @param {boolean} includeErrorBody Whether API error payloads should be surfaced to callers.
 * @returns {Promise<any>} A promise that resolves to the parsed JSON payload.
 */
const parseResponseJson = async (response, includeErrorBody = false) => {
  if (!response.ok) {
    if (!includeErrorBody) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const message = await parseErrorMessage(response);
    throw new Error(`HTTP error! status: ${response.status} - ${message}`);
  }
  return response.json();
};

/** Fetches the airplane list. */
export const fetchAirplanes = async () => {
  const response = await fetch(buildRequestTarget('/airplanes'));
  return parseResponseJson(response);
};

/**
 * Fetches seat and booking details for a flight.
 *
 * @param {string} flightNumber The flight identifier.
 * @returns {Promise<any>} A promise that resolves to the airplane detail payload.
 */
export const fetchAirplaneDetails = async (flightNumber) => {
  const safeFlightNumber = encodePathSegment(flightNumber, 'flight number');
  const response = await fetch(buildRequestTarget(`/airplanes/${safeFlightNumber}`));
  return parseResponseJson(response);
};

/** Fetches the customer list. */
export const fetchCustomers = async () => {
  const response = await fetch(buildRequestTarget('/customers'));
  return parseResponseJson(response);
};

/**
 * Creates a new customer.
 *
 * @param {object} customerData The customer payload to submit.
 * @returns {Promise<any>} A promise that resolves to the created customer.
 */
export const addCustomer = async (customerData) =>
  parseResponseJson(
    await fetch(buildRequestTarget('/customers'), {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify(customerData),
    }),
    true,
  );

/**
 * Creates a seat booking.
 *
 * @param {object} bookingData The booking payload to submit.
 * @returns {Promise<any>} A promise that resolves to the created booking.
 */
export const createBooking = async (bookingData) =>
  parseResponseJson(
    await fetch(buildRequestTarget('/bookings'), {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify(bookingData),
    }),
    true,
  );

/**
 * Fetches details for a single customer.
 *
 * @param {string} customerId The customer identifier.
 * @returns {Promise<any>} A promise that resolves to the customer detail payload.
 */
export const fetchCustomerDetails = async (customerId) => {
  const safeCustomerId = encodePathSegment(customerId, 'customer id');
  const response = await fetch(buildRequestTarget(`/customers/${safeCustomerId}`));
  return parseResponseJson(response, true);
};

/**
 * Cancels a booking.
 *
 * @param {string|number} bookingId The booking identifier.
 * @returns {Promise<any>} A promise that resolves to the cancellation response.
 */
export const cancelBooking = async (bookingId) =>
  parseResponseJson(
    await fetch(buildRequestTarget(`/bookings/${encodePathSegment(bookingId, 'booking id')}`), {
      method: 'DELETE',
    }),
    true,
  );

/** Fetches all bookings. */
export const fetchBookings = async () => {
  const response = await fetch(buildRequestTarget('/bookings'));
  return parseResponseJson(response, true);
};

/**
 * Swaps the seats for two bookings.
 *
 * @param {string|number} bookingId1 The first booking identifier.
 * @param {string|number} bookingId2 The second booking identifier.
 * @returns {Promise<any>} A promise that resolves to the swap response.
 */
export const swapSeats = async (bookingId1, bookingId2) =>
  parseResponseJson(
    await fetch(buildRequestTarget('/bookings/swap'), {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({
        bookingId1: encodePathSegment(bookingId1, 'booking id 1'),
        bookingId2: encodePathSegment(bookingId2, 'booking id 2'),
      }),
    }),
    true,
  );
