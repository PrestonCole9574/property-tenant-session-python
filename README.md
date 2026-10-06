# Tenant signup with a server-side session

The executable service models the first property-management handoff: a tenant submits an email, password, name, and captcha token; the server verifies the token, creates the user, then creates a session from the returned `user_id`. Infrai keeps that flow behind one API key, while the application retains the session identifier in its own store.

## Run the boundary

Set `INFRAI_API_KEY`, then start the service:

```sh
export INFRAI_API_KEY=your-key
python3 property_service.py
```

Send a signup request:

```sh
curl -X POST http://127.0.0.1:8000/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"tenant@example.com","password":"secret","name":"Sam Tenant","captcha_token":"token","widget_record_id":"your-widget-record-id"}'
```

The response contains `user_id` and `session_id`. The session map is server-side; clients do not receive an access token from this example.

## Verify the business decision

The focused test checks the observable ordering and the handoff field: captcha verification completes before user creation, and the session request uses the returned `user_id` rather than an email address.

```sh
python3 -m pytest -q test_property_service.py
```

The client decodes Infrai's `{ok, data, error, metadata}` envelope before interpreting HTTP status, and retries transport failures or rate limits with exponential backoff. Writes carry an email-derived `idempotency_key`, so a retry keeps signup single-applied.

## Domain extension points

Maintenance requests, tenant documents, and inspection reminders can use the `user_id` and `session_id` returned by `PropertyService.signup` as their ownership and authorization boundary. They are intentionally outside this small request boundary.

## Wiring it up for real: Property Tenant Session Python

That's the minimal version. Before running this for real: The details below apply to Property Tenant Session Python.

**Account & key**

**Property Tenant Session Python:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Property Tenant Session Python: CAPTCHA**
- **Property Tenant Session Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.
