# ZConnect Odoo Documentation

Welcome to the central documentation repository for **ZConnect** — Zimbabwe's premier parcel delivery and logistics platform. 
This documentation outlines the complete Odoo backend implementation, providing a full view of the architecture, modules, APIs, workflows, and configurations.

**Developed by**: Tatenda Tembo

## Table of Contents
1. [Executive Summary & Introduction](#executive-summary)
2. [Architecture & Design Rationale](architecture.md)
3. [Module Catalogue](modules.md)
4. [Data Model & Database Architecture](data-model.md)
5. [Business Workflows](workflows.md)
6. [API Reference](api-reference.md)
7. [User Interface & Menus](ui-and-menus.md)
8. [Security & Quality Assurance](security-and-quality.md)
9. [Deployment & Operations](deployment-and-operations.md)
10. [Proposal Traceability](proposal-traceability.md)
11. [Architectural Decisions](decisions.md)
12. [Changelog](CHANGELOG.md)

## Executive Summary
ZConnect leverages **Odoo 19 Enterprise** as its core ERP backend, taking advantage of its robust security, ORM, workflow engine, and QWeb templating. The system uses a highly modular architecture (small, focused custom addons) to manage the end-to-end lifecycle of parcel delivery—from customer bookings on the portal/app, to driver dispatch, proof of delivery, and payment processing.

The backend exposes a JSON-RPC API for the companion ZConnect Flutter mobile application, ensuring real-time syncing of shipment statuses and driver locations.

## Why Odoo Enterprise & PostgreSQL 16?
- **Odoo Enterprise**: Chosen for its superior mobile responsiveness, advanced accounting features, improved web client performance, and professional support. It provides the necessary foundation for scaling logistics operations.
- **PostgreSQL 16**: Chosen because it is highly stable, performant for geospatial data (PostGIS readiness), and has mature JSONB support which is critical for Odoo's dynamic fields. We specifically avoided version 18 as it is too bleeding-edge for production enterprise ERP deployments where data integrity and proven stability are paramount.

## Installation & Configuration
1. Clone this repository into your Odoo `addons-path`.
2. Ensure Odoo 19 Enterprise source is available.
3. Install dependencies: `pip install -r requirements.txt` (if applicable).
4. Run Odoo:
   ```bash
   python odoo-bin -c odoo.conf -d zconnect_db -u zconnect_dashboard,zconnect_portal,zconnect_api,zconnect_shipment,zconnect_dispatch,zconnect_driver,zconnect_payment
   ```
5. Navigate to `http://localhost:8070` to access the ZConnect web interface.

*For detailed operational guidelines, see [Deployment & Operations](deployment-and-operations.md).*
