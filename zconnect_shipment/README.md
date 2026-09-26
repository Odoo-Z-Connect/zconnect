# Zimbabwe Connect — Shipment Core (`zconnect_shipment`)

## Purpose
The `zconnect_shipment` module implements the central logistics aggregate (`zconnect.shipment`) for Zimbabwe Connect.

## Architecture (ADR-005)
- **`res.partner`**: Master customer and contact identity.
- **`fleet.vehicle`**: Master vehicle records and capacity attributes.
- **`zconnect.pricing`**: Deterministic quote calculation and snapshotting.
- **`zconnect.shipment`**: The central logistics transaction.

## Lifecycle State Machine
```text
Draft Booking (draft)
     ↓ action_calculate_quote()
Quoted (quoted)
     ↓ action_prepare_payment()
Awaiting Payment (awaiting_payment)
     ↓ action_confirm()  [Seals Financial Snapshot]
Confirmed (confirmed)
     ↓ (future zconnect_dispatch)
Driver Assigned (assigned)
     ↓
En Route to Pickup (en_route_pickup)
     ↓
Picked Up (picked_up)
     ↓
In Transit (in_transit)
     ↓
Near Delivery (near_delivery)
     ↓
Delivered (delivered)
```
*Also supports `cancelled` and `exception` states.*

## Immutable Pricing Snapshot
When a quote is calculated in `draft` or `quoted`, the estimated rate breakdown is stored.
When `action_confirm()` is executed, `is_pricing_confirmed` is set to `True`, permanently sealing:
- `base_fare`
- `distance_charge`
- `weight_charge`
- `zone_charge`
- `subtotal`
- `minimum_fare`
- `total_amount`
- `pricing_rule_id`
- `pricing_calculated_at`

Future changes to pricing tariffs in `zconnect.pricing.rule` never alter confirmed historical shipments.
