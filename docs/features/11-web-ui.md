# 11 · Web UI

React 18 with Vite, Tailwind CSS v4 and React Router. It uses a light, Bootstrap-like style. Every API call goes
through `src/services/api.js`, and auth state lives in `src/hooks/useAuth.jsx`.

| Screen | Route | Needs | What it does |
|---|---|---|---|
| Home | `/` | — | Brand banner, quick search, services, popular destinations, club tiers |
| Login / Join | `/login` | — | Member login and self-registration (no demo accounts shown) |
| Staff sign in | `/admin/login` | — | Admin login; the only page listing sandbox accounts |
| Search | `/search?…` | — | One-way (return date empty) or round trip, cabin, adults / children / infants; itinerary cards with party total and per-type fares; the URL holds the search |
| Book | `/book?out=&ret=&class=&a=&c=&i=` | guest or member | Itinerary → passengers (one row per searched type) → review → mock payment → confirmation with PNR |
| Manage booking | `/booking` | guest or member | PNR + last name lookup, check-in link, cancel; members also see "Your trips" |
| Check-in | `/checkin` | guest or member | PNR + last name → choose passengers → through check-in → printable boarding passes, one per segment |
| Admin dashboard | `/admin` | `admin` | Record counts |
| Admin bookings | `/admin/bookings` | `admin` | All bookings, including guests; filter by PNR, user or status; view, cancel, delete |
| Admin flights | `/admin/flights` | `flights:write` | Paged, filterable schedule table; add and edit flights |

Branding: the logo (`src/logo.png`) is used in the header, the footer and the browser tab (`public/favicon.png`), and
`src/banner.png` is the home page hero.

Behaviour:
- Navigation links and routes appear only if the token has the scope they need. When a signed-out user opens a
  protected route, they are sent to login and brought back afterwards.
- A 401 from the API logs the user out.
- Every screen handles loading, success and error states, and shows the backend's error message (for example,
  *"Payment was rejected. Your seats have not been reserved."*).
- In development, Vite proxies `/api`, `/docs`, `/redoc` and `/openapi.json` to the backend.
