# sitescore-commerce 0.1.0

FAZ 6.0 commerce/order and Stripe Checkout foundation, based on frozen `main` SHA `0e370940ee5c8c1253db72fa7e33078fb4ef3b2c` on branch `faz6/6-0-commerce-order-checkout`.

Public surface: `POST /v1/orders` with required `Idempotency-Key`. The only product is `location_report_v1`. Caller purchase intent is validated against commerce-local models that mirror the frozen four-sector `AnalysisRequest` contract; runtime does not import `sitescore_api`.

6.0 creates a durable PostgreSQL `commerce` order and a server-created Stripe hosted Checkout Session. It does **not** establish payment truth. The only authored state tuple is `pending_payment / pending / not_started`.

Configuration: `SITESCORE_COMMERCE_DATABASE_URL`, `STRIPE_SECRET_KEY`, `STRIPE_PRICE_LOCATION_REPORT_V1`, `STRIPE_API_VERSION=2026-07-29.dahlia`, `COMMERCE_SUCCESS_URL_BASE`, `COMMERCE_CANCEL_URL_BASE`, optional `COMMERCE_ENV`.

Stripe SDK is exactly `stripe==15.4.0`; Checkout uses the server-owned configured Price ID, quantity 1, `mode=payment`, `ui_mode=hosted`, and card-only payment surface. Caller amounts, currency, Stripe identifiers, redirects, discounts, payment state and analytical/report authority are rejected as unknown fields.

See `docs/CHECKPOINT_6_0_COMMERCE_ORDER_STRIPE_CHECKOUT.md` for detailed invariants and recovery semantics.
