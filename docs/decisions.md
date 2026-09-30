# Architectural Decisions & Rationale

This document captures the primary engineering decisions made during the development of the ZConnect Odoo backend.

## 1. Modular Micro-Addon Structure
- **Decision**: Break the project into 8+ small modules (`zconnect_shipment`, `zconnect_dispatch`, `zconnect_api`, etc.) rather than one monolithic module.
- **Rationale**: While a monolith is faster to initially scaffold, logistics platforms are inherently complex. By separating concerns, we ensure that a bug introduced in the API (`zconnect_api`) does not crash the core shipment pricing engine (`zconnect_shipment`). It also allows us to cleanly map Odoo security groups to specific modules.

## 2. API as a Separate Module (`zconnect_api`)
- **Decision**: Create a dedicated module for all JSON-RPC / HTTP endpoints utilized by the Flutter mobile application.
- **Rationale**: Mobile apps have strict versioning requirements because users do not update their apps immediately. By isolating the API, we can safely introduce `zconnect_api_v2` in the future without interfering with the internal Odoo web interface or the customer portal.

## 3. Custom Dashboard via OWL (Odoo Web Library)
- **Decision**: Override standard Odoo XML list views to build a highly customized, branded dashboard in `zconnect_dashboard`.
- **Rationale**: Logistics dispatchers need instantaneous, bird's-eye visibility of their operations. Standard Odoo list views require manual refreshing and lack visual prominence. The custom OWL dashboard uses `Chart.js` and custom CSS (implementing the ZConnect brand colors `#e0ebe6`, `#3db64c`, `#424243`, `#289131`, `#bbb09a`) to provide a real-time, premium user experience.

## 4. Bypassing Record Rules in the Customer Portal
- **Decision**: Use `.sudo()` for assignment lookups within the public/customer portal booking flow.
- **Rationale**: We implemented a strict `ir.rule` that prevents drivers from seeing other drivers' assignments. However, when a customer books a shipment via the portal, the system needs to evaluate potential assignments. Because the public user is not a driver, the rule blocked the transaction, resulting in a 403 Forbidden error. Elevating privileges via `.sudo()` exclusively during this specific creation route safely bypasses the read restriction without compromising the global security posture.

## 5. PostgreSQL 16
- **Decision**: Standardize deployment on PostgreSQL 16.
- **Rationale**: Version 16 provides the optimal balance of stability and performance for JSONB operations (which Odoo relies on heavily). We specifically chose not to adopt Postgres 18 as it lacks the years of battle-testing required for a mission-critical ERP database storing financial and logistical data.
