# Module Catalogue & Reference

The ZConnect platform is built using a micro-module architecture within Odoo. Each module has a specific domain of responsibility.

## Core Modules

| Module Name | Technical Name | Purpose | Dependencies |
| :--- | :--- | :--- | :--- |
| **ZConnect Base** | `zconnect_base` | Defines base security groups, common mixins, and system-wide configurations. | `base`, `mail` |
| **ZConnect Shipment** | `zconnect_shipment` | Core data model for `zconnect.shipment`. Handles shipment states, pricing calculations, and addresses. | `zconnect_base` |
| **ZConnect Driver** | `zconnect_driver` | Manages driver profiles, vehicles, verification states, and active locations. | `zconnect_base` |
| **ZConnect Dispatch** | `zconnect_dispatch` | The assignment engine. Connects Shipments to Drivers, handles offer acceptance/rejection, and IR rules for driver visibility. | `zconnect_shipment`, `zconnect_driver` |
| **ZConnect Portal** | `zconnect_portal` | Web-based customer facing portal. Allows customers to book shipments, view statuses, and handle payments. | `zconnect_shipment`, `website` |
| **ZConnect API** | `zconnect_api` | JSON-RPC API layer for the Flutter mobile application. Exposes endpoints for driver tracking, assignment management, and POD. | `zconnect_dispatch`, `zconnect_pod` |
| **ZConnect Dashboard**| `zconnect_dashboard` | Backend KPI dashboard for dispatchers and admins. Features real-time charts utilizing the ZConnect brand colors. | `zconnect_shipment` |
| **ZConnect POD** | `zconnect_pod` | Proof of Delivery module. Handles signature capture, photo evidence, and delivery notes. | `zconnect_shipment` |
| **ZConnect Payment** | `zconnect_payment` | Integrates local Zimbabwean payment gateways (e.g. Paynow) into the shipment lifecycle. | `zconnect_shipment`, `payment` |

## Module Deep Dive: `zconnect_dispatch`
- **Purpose**: Connects demand (shipments) with supply (drivers).
- **Models Defined**: `zconnect.dispatch.assignment`
- **Security**: Contains complex record rules (`ir.rule`) ensuring drivers only see their own assignments, while admins see all. A known limitation historically caused 403 Forbidden errors when creating portal shipments, which was resolved by leveraging `sudo()` during portal lookup flows to bypass driver-only strict rules until assignment is finalized.
- **Workflow**: `draft` -> `offered` -> `accepted` -> `in_progress` -> `completed` / `rejected`.

## Module Deep Dive: `zconnect_api`
- **Purpose**: Bridge the Odoo ORM to the Flutter mobile application.
- **Controllers**: See [API Reference](api-reference.md).
- **Design Rationale**: By strictly separating API routes into their own module, we ensure that changes to backend views or portal templates do not accidentally break the mobile app parsing logic.

*For complete dependency graphs, view the `__manifest__.py` file in each module directory.*
