# Zimbabwe Connect — Pricing Engine (`zconnect_pricing`)

## Purpose
The `zconnect_pricing` module provides a configurable, deterministic calculation engine for logistics quotes across all vehicle categories and service zones for Zimbabwe Connect.

## Core Models
1. **`zconnect.pricing.rule`**: Configurable tariff rules specifying:
   - `vehicle_category`: Reuses category vocabulary from `zconnect_fleet` (`fleet.vehicle`).
   - `base_fare`: Fixed initiation charge.
   - `price_per_km`: Distance variable charge.
   - `price_per_kg`: Cargo weight variable charge.
   - `minimum_fare`: Price floor protection.
   - `effective_from` / `effective_to`: Date validity windows.
2. **`zconnect.pricing.zone`**: Service area and surcharge zones (e.g., Harare Urban, Peri-Urban, Outskirts).

## Calculation Formula
```text
distance_charge = distance_km * price_per_km
weight_charge   = package_weight_kg * price_per_kg
vehicle_charge  = 0.0 (baseline covered by rule category)
zone_charge     = zone.surcharge
subtotal        = base_fare + distance_charge + weight_charge + vehicle_charge + zone_charge
total_amount    = max(subtotal, minimum_fare)
```

## Architectural Decoupling & Price Snapshotting (ADR-004)
- **Configuration vs Snapshot**: Pricing rules are configuration. When a quote is calculated, `compute_quote()` returns a comprehensive dictionary with all charge breakdowns and the applicable currency.
- **Future Consumption (`zconnect_shipment`)**: The calculated breakdown is snapshotted directly onto fields on the shipment record. Future tariff adjustments never modify past shipment financial records.
