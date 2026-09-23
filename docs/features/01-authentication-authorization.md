# 01 · Authentication & authorization

## Purpose
Members and admins sign in with a signed access token. **Guests can book and manage trips without an account**,
using the airline-style secrets described below. Tier-based services and all administration need a token. Access is
granted per operation through OAuth2 **scopes**, and the scopes a token carries depend on the user's role and
membership tier.

## How it works
- **Flow:** OAuth2 *resource owner password credentials* grant (RFC 6749 §4.3) at `POST /api/auth/token`. The
  request is form-encoded: `username`, `password`, and optionally `scope`.
- **Token:** a JWT signed with HS256. It contains the standard claims `iss`, `sub` (user ID), `iat`, `exp` and `scope`
  (space-separated), plus the display claims `username`, `name`, `role` and `tier`. It is valid for 60 minutes by
  default (`ACCESS_TOKEN_MINUTES`).
- **Validation:** each protected endpoint declares the scopes it needs (`Security(get_principal, scopes=[…])`). A token
  is rejected with **401** if it is missing, invalid or expired, or if its user no longer exists. A valid token that
  lacks a required scope is rejected with **403**.
- **Passwords:** stored as PBKDF2-SHA256 hashes with a random salt and 200,000 iterations, using only the standard library.

> **Why a built-in issuer?** The sandbox signs its own JWTs so it runs offline with no accounts to set up. The token
> format and scope checks follow OAuth2/JWT conventions, so an external free provider can replace the issuer. For
> example, Keycloak (self-hosted), Auth0 or Okta free tiers: validate their RS256 tokens against the provider's JWKS
> in `auth/security.decode_access_token`, and map the provider's roles and groups to the scopes below.

## Scopes

| Scope | Granted to | Allows |
|---|---|---|
| `profile` | customers, admin | `GET /auth/me`, own user record |
| `passengers:write` | customers, admin | create / modify / delete own passengers |
| `bookings:read` | customers, admin | own bookings, PNR + last-name retrieval, payments, tickets |
| `bookings:write` | customers, admin | create, change, cancel own bookings |
| `payments:write` | customers, admin | reserved for payment operations (payments are made on the hosted page) |
| `checkin:write` | customers, admin | check in by PNR + last name, change seat |
| `ssr:read` | customers, admin | view SSRs and eligibility |
| `ssr:write` | customers whose tier allows any SSR, admin | create / cancel SSRs (with the matching type scope) |
| `ssr:MEAL`, `ssr:LOUNGE`, `ssr:WHEELCHAIR`, `ssr:BASSINET`, `ssr:EXCESS_BAGGAGE` | **only if the user's tier allows that service**, admin | request that specific service |
| `flights:write` | admin | create / modify flight schedules |
| `tickets:write` | admin | manually issue / cancel tickets |
| `admin` | admin | list all users, bookings, check-ins, tickets; aircraft; dashboard |

**Tier-based write permission.** A Bronze member's token has `ssr:MEAL` and `ssr:WHEELCHAIR`, but not `ssr:LOUNGE`.
A client holding that token cannot create a lounge request, even if the UI is bypassed. The SSR service also re-checks
the booking owner's *current* tier, so a stale token issued before a downgrade can't be used.

If a client asks for specific scopes, it gets only the requested scopes that the user is allowed; that is how a client
gets a narrower, least-privilege token. If it asks for none, it gets every scope the user is allowed.

## Guest access
These endpoints work **without a token**. If a token is sent, it must be valid and carry the listed scope.

| Endpoint | How guests are authorised |
|---|---|
| `POST /passengers` | creates an unowned passenger |
| `POST /bookings` | creates a held booking owned by nobody |
| `GET /payment-sessions/{session_id}`, `POST …/pay` | the secret session id in the payment URL |
| `GET /bookings/pnr/{pnr}`, `GET /bookings/{id}`, `PUT` / `change` / `cancel` / `history` | a passenger's `last_name` |
| `POST /checkins/validate`, `POST /checkins`, `GET /tickets/{id}` | PNR + `last_name` |

Guest bookings have `user_id = null`. They cannot add SSRs, because there is no member tier. An unowned passenger can
be used only while it has never been on a booking, so one guest can't reuse another guest's passenger records.

## Ownership rules
- Customers can only see and change their own passengers, payments, bookings, check-ins and SSRs. Anything that
  belongs to another user returns 404, so the API doesn't reveal that it exists.
- Changing or cancelling a booking needs the owner, an admin, or a matching passenger `last_name` (**403** otherwise).
- Airline convention: anyone holding the **PNR and a passenger's last name** can retrieve that itinerary and check in.
  Any authenticated user can do this, but the last name is always required. See [03](03-booking-pnr.md).
- Admins act on any record. Payment and booking requests may include `user_id` to act on behalf of a customer.

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/token` | public | Password grant → `{access_token, token_type, expires_in, scope}` |
| POST | `/api/auth/register` | public | Create a customer account (Bronze tier) |
| GET | `/api/auth/me` | `profile` | Profile, tier, token scopes and allowed scopes |

Public (no token): `/api/health`, airports, routes, cabin classes, tiers, fares, flight search / list / detail,
itinerary search and the SSR catalog.

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/token -d 'username=john&password=password123' | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" localhost:8000/api/auth/me
```

Swagger UI (`/docs`) has an **Authorize** button that runs the same flow.

## Sandbox accounts
These are listed only on the staff sign-in page (`/admin/login`), not on the public login page. Customers register
their own accounts.


| Username | Password | Role / tier |
|---|---|---|
| `admin` | `admin` | Admin (all scopes) |
| `john`, `emma` | `password123` | Gold |
| `priya`, `sofia` | `password123` | Silver |
| `ahmed`, `rahul` | `password123` | Bronze |

## Configuration
`JWT_SECRET` (**set this in any shared environment**), `ACCESS_TOKEN_MINUTES`.

## UI
The UI has a public login / registration page (`/login`) and a staff sign-in page (`/admin/login`) that lists the
sandbox accounts. It keeps the token in `localStorage`. It sends the token as a bearer header,
logs out on 401, and shows navigation items and routes only when the token has the scope they need (for example,
Admin needs `admin`). Hiding things in the UI is a convenience; the backend enforces every rule.
