# Security & Quality Assurance

## Authentication & Authorization
ZConnect uses Odoo's built-in `res.groups` and `ir.rule` framework to strictly enforce data isolation.

### User Groups
1. **ZConnect / Customer**: Standard portal user. Can only read and write their own `zconnect.shipment` records.
2. **ZConnect / Driver**: Assigned to driver accounts. Allows access to the mobile API endpoints and read access to `zconnect.dispatch.assignment` records linked to their `partner_id`.
3. **ZConnect / Dispatcher**: Can view all shipments and assign drivers, but cannot alter global configuration.
4. **ZConnect / Administrator**: Full access to all models, settings, and financial data.

### Record Rules (`ir.rule`)
- **Driver Own Shipments**: Ensures drivers can only query assignments where `driver_id.user_id == user.id`. 
  - *Historical Fix*: This rule previously caused a 403 Forbidden error during portal shipment creation because the portal controller attempted to read assignments before a driver was attached. This was fixed by utilizing `.sudo()` context elevation strictly within the portal creation route, ensuring security without breaking functionality.

## API Security
- **No Hardcoded Secrets**: All API endpoints authenticate via Odoo session cookies. No hardcoded API keys are present in the controller logic.
- **Input Validation**: The API controllers (`zconnect_api/controllers/api.py`) cast IDs to integers (`<int:shipment_id>`) in the Werkzeug routing layer, preventing basic SQL injection and path traversal attacks.

## Testing & Quality Assurance
- **Unit Tests**: The repository contains Odoo standard Python `unittest` cases under `tests/`. (e.g. `test_zconnect_api.py`, `tests_step11_e2e.py` found in the root utility scripts).
- **Frontend Validation**: The customer portal strictly uses HTML5 required attributes and JavaScript type-casting (`parseFloat()`) to ensure bad data (e.g. string weights) cannot be submitted to the XML-RPC backend.

### Known Gaps & Limitations
- **Rate Limiting**: Currently, the public `/api/v1/zconnect/auth/login` endpoint does not have explicit rate-limiting implemented in Odoo. In production, this must be handled by an Nginx reverse proxy (e.g. `limit_req`).
- **CORS Configuration**: The API controllers use `cors='*'` for ease of development. Before production deployment, this MUST be locked down to the specific domain serving the web app or restricted entirely for mobile-only traffic.
