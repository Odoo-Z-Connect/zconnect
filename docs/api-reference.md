# API Reference

The ZConnect platform exposes a robust JSON-RPC API for the companion Flutter mobile application. The API is housed in the `zconnect_api` module to ensure strict separation from the core Odoo backend controllers.

## Base URL
All endpoints are relative to your Odoo base URL (e.g., `https://zconnect.co.zw`).

## Authentication
Authentication relies on standard Odoo session cookies. The Flutter app must POST to `/api/v1/zconnect/auth/login` to obtain the `session_id` cookie, which must be passed in the headers of all subsequent requests.

---

## 1. Authentication Endpoints

### POST `/api/v1/zconnect/auth/login`
- **Auth**: Public
- **Body**:
  ```json
  {
    "params": {
      "db": "odoo_enterprise",
      "login": "driver@example.com",
      "password": "secretpassword"
    }
  }
  ```
- **Returns**: User metadata (name, partner_id, session details). Sets the session cookie.

### POST `/api/v1/zconnect/auth/signup`
- **Auth**: Public
- **Body**: Requires `name`, `login`, `password`, `phone`, and `account_type`.

---

## 2. Customer Endpoints

### GET `/api/v1/zconnect/shipments`
- **Auth**: User
- **Returns**: A list of all shipments belonging to the authenticated customer.

### POST `/api/v1/zconnect/shipments`
- **Auth**: User
- **Body**: Requires `pickup_address`, `delivery_address`, `vehicle_category`, and `weight_kg`.
- **Returns**: The ID of the newly created `zconnect.shipment` record.

### POST `/api/v1/zconnect/shipments/<id>/confirm`
- **Auth**: User
- **Action**: Confirms a draft shipment.

---

## 3. Driver Endpoints

### GET `/api/v1/zconnect/driver/assignments`
- **Auth**: User (Driver)
- **Returns**: A list of assignments specifically offered to or accepted by the authenticated driver. Enforced by Odoo record rules.

### POST `/api/v1/zconnect/assignments/<id>/accept`
- **Auth**: User (Driver)
- **Action**: Transitions an assignment from `offered` to `accepted`. 

### POST `/api/v1/zconnect/shipments/<id>/status`
- **Auth**: User (Driver)
- **Body**: 
  ```json
  {
    "params": {
      "status": "en_route_pickup" // or in_transit, etc.
    }
  }
  ```
- **Action**: Updates the physical status of the shipment.

### POST `/api/v1/zconnect/shipments/<id>/pod`
- **Auth**: User (Driver)
- **Body**: Requires `signature_image` (base64) and/or `photo_image` (base64).
- **Action**: Generates a Proof of Delivery record and finalizes the shipment.

---

## Security & Rate Limiting
- **CSRF Protection**: CSRF is explicitly disabled (`csrf=False`) on these endpoints because they are designed for a stateless-style mobile client that relies on session cookies rather than form tokens.
- **CORS**: Configured to allow cross-origin requests (`cors='*'`) on auth endpoints to support web-based testing, but should be restricted in production.
