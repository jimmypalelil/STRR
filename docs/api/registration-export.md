# Registration Export API

## Purpose

The Registration Export API provides current registration snapshots for:

- `HOST`
- `PLATFORM`
- `STRATA_HOTEL`

It supports two client use cases:

- Incremental polling for the Ministry of Finance.
- Targeted registration lookup for the Data Portal, managed by the Short-Term Rental branch.

Each returned registration is a complete current snapshot, not a field-level diff.

## HTTP method

The final HTTP method will be confirmed during implementation and compatibility testing. Consumers must not assume that the newer `QUERY` method will be the primary production method.

`QUERY` is under consideration for a safe, idempotent body-based request. If client libraries, gateways, WAFs, or other infrastructure do not support it, an equivalent `POST` endpoint will be provided as needed. Method availability will be confirmed before integration begins.

Potential request:

```http
QUERY /registrations/export HTTP/1.1
Content-Type: application/json
Accept: application/json
Authorization: Bearer <token>
```

If provided, the POST compatibility endpoint will use the same path, JSON body, authentication, and response contract.

## Authentication

### Ministry authentication

The Ministry integration uses a machine-to-machine credential for unattended incremental polling.

### Data Portal authentication

The Data Portal may access the API using either:

- A machine-to-machine credential for backend and unattended requests.
- An IDIR user token for portal UI requests when the user has `ceu_staff` or `ceu_admin`.

The API must validate the token and required role before returning data. Allowed registration types and registration-ID scope for each IDIR role must be confirmed with the Data Portal and security teams. Machine-to-machine and IDIR access should be audited using their respective identities.

## Common request fields

| Field          | Description                                                                  |
| -------------- | ---------------------------------------------------------------------------- |
| `updatedSince` | Optional ISO 8601 timestamp. Returns registrations changed after this value. |
| `cursor`       | Opaque cursor returned by the previous page. Do not parse or construct it.   |
| `limit`        | Optional page size. Defaults to `100`; maximum allowed value is `500`.       |

The API should reject a non-positive, non-numeric, or greater-than-`500` `limit` with a client error rather than silently clamping it. The server may read `limit + 1` records internally, but returns no more than `limit` items.

## Ministry of Finance request

```json
{
  "updatedSince": "2026-09-01T00:00:00Z",
  "cursor": "<opaque cursor>",
  "limit": 500
}
```

For the initial full synchronization, omit `updatedSince` and `cursor`.

## Data Portal request

```json
{
  "registrationIds": [4821, 4920, 5177],
  "limit": 100,
  "cursor": "<opaque cursor>"
}
```

`registrationIds` is required for a targeted Data Portal request. The API must enforce a maximum list size and automatically deduplicate repeated IDs. Each registration appears at most once in the response.

## Response

```json
{
  "items": [
    {
      "registrationId": 4821,
      "registrationNumber": "H123456789",
      "registrationType": "HOST",
      "status": "ACTIVE",
      "updatedDate": "2026-09-07T18:42:11.203000",
      "rentalUnit": {},
      "contacts": []
    }
  ],
  "nextCursor": "<opaque cursor or null>"
}
```

- A non-null `nextCursor` means another page is available.
- `nextCursor: null` means the request is complete.
- Clients must persist the cursor only after successfully processing the page.
- A Data Portal targeted cursor must not be reused for the Ministry of Finance global feed.

For targeted Data Portal requests, the response may also contain per-ID errors:

```json
{
  "items": [...],
  "errors": [
    {
      "registrationId": 99999,
      "code": "NOT_FOUND"
    }
  ],
  "nextCursor": "<opaque cursor or null>"
}
```

The `code` is stable and required. A `message` may be included for diagnostics but is not intended for client logic. Initial codes include:

- `INVALID_ID`
- `NOT_FOUND`
- `NOT_AVAILABLE`

`NOT_AVAILABLE` prevents authorization failures from revealing whether a registration exists. Duplicate IDs do not produce duplicate errors.

## Registration payloads

Every item includes `registrationId`, `registrationNumber`, `registrationType`, `status`, and `updatedDate`.

- `HOST`: rental unit details and host, co-host, and property-manager contacts.
- `PLATFORM`: business details, representatives, brands, licence information, and notification/takedown fields.
- `STRATA_HOTEL`: business details, location, representatives, buildings, category, and unit listings.

Contact payloads include name, preferred name, mailing address, phone, fax, email, and applicable role information.

The API does not return `dateOfBirth`, `socialInsuranceNumber`, `businessNumber`, SIN, or CRA tax-number fields in contact payloads.
