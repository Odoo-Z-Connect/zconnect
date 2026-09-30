# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- Added `docs/` directory containing comprehensive technical and architectural documentation mapping the Odoo implementation.
- Added Postman Collection `ZConnect_API_Postman_Collection.json` for the Flutter mobile application endpoints.
- Added hidden `current_partner_id` field in the customer portal `portal_templates.xml` to securely pass the customer ID to the XML-RPC endpoint.

### Changed
- **Dashboard Branding**: Updated `zconnect_dashboard/static/src/scss/dashboard.scss` to use the official ZConnect brand colors (`#e0ebe6`, `#3db64c`, `#424243`, `#289131`, `#bbb09a`) for the KPI cards instead of standard Odoo Tailwind colors.
- **Portal Shipment Creation**: Updated the JS payload in `portal_templates.xml` to correctly map `pickup_phone` -> `pickup_contact_phone` and `delivery_phone` -> `delivery_contact_phone` to match the `zconnect.shipment` backend model.
- **Portal Shipment Creation**: Added `pickup_latitude` and `pickup_longitude` (and delivery equivalents) to the JS payload from the hidden form inputs.

### Fixed
- Fixed a bug where a `ValueError: Invalid field 'pickup_phone'` caused the customer portal to silently fail and redirect to an empty `/my/shipments` list when attempting to book a shipment.
- Fixed 403 Forbidden errors when creating portal shipments by using `.sudo()` in the controller for assignment evaluations, bypassing the strict `Driver Own Shipments` record rule.
