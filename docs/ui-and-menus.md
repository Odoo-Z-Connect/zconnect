# User Interface & Menus

## Backend Menu Catalogue

The backend interface is primarily built for Admins and Dispatchers.

| Menu Name | Parent Menu | Destination / Action | User Role |
| :--- | :--- | :--- | :--- |
| **ZConnect** | [Root] | Dashboard View | Dispatcher, Admin |
| **Dashboard** | ZConnect | `zconnect_dashboard.action_zconnect_dashboard` | Dispatcher, Admin |
| **Shipments** | ZConnect | `zconnect_shipment.action_shipment_list` | Dispatcher, Admin |
| **Drivers** | ZConnect | `zconnect_driver.action_driver_list` | Admin |
| **Configuration** | ZConnect | Settings & Categories | Admin |

## Design Language & Branding

ZConnect employs a custom design language tailored to its brand identity.

### Brand Colors
The backend dashboard (`zconnect_dashboard`) and the customer portal (`zconnect_portal`) utilize the official ZConnect brand colors:
- **Light Green**: `#e0ebe6` (Used for subtle backgrounds and badges)
- **Primary Green**: `#3db64c` (Primary call-to-action buttons, active statuses)
- **Dark Grey**: `#424243` (Headers, solid KPI cards)
- **Dark Green**: `#289131` (Hover states, Delivered status)
- **Grey Orange**: `#bbb09a` (Secondary metrics, In Transit statuses)

### Typography
The entire platform overrides standard Odoo fonts to use **Poppins** and **Roboto** for a modern, approachable feel.

### Dashboard UX
The primary operational dashboard (`zconnect_dashboard/static/src/xml/dashboard.xml`) abandons standard Odoo list views in favor of a real-time, OWL-based (Odoo Web Library) interactive interface. It features:
- **KPI Cards**: Instantly showing total, active, in-transit, and delivered shipments.
- **Chart.js Integrations**: Providing visual trends on shipment volumes and delivery velocities.
- **Skeleton Loading**: Ensuring the interface feels responsive and premium even during heavy data fetches.

## Customer Portal UX
The customer booking portal (`/my/shipments/new`) is designed as a seamless, glassmorphic wizard. 
- It uses a translucent header that blends into the hero section.
- Form inputs are validated via HTML5 and JS before submission.
- Real-time price calculators dynamically update the UI without requiring page reloads, providing an immediate feedback loop for the user.
