# Zimbabwe Connect — Base Module (`zconnect_base`)

## Overview
The `zconnect_base` module establishes the foundational security, partner extensions, sequence generation, and base menu hierarchy for the **Zimbabwe Connect Odoo 19 Enterprise** logistics platform.

---

## Key Architectural Highlights

### 1. `res.partner` Extension (No Duplicate Customer Model)
Following standard Odoo architectural principles, Zimbabwe Connect does not create a bespoke `zconnect.customer` model. Instead, standard `res.partner` is inherited and augmented with:
* `zconnect_is_customer` (Boolean)
* `zconnect_is_driver` (Boolean)
* `zconnect_customer_code` (Char, unique sequence e.g., `CUS-00001`)

### 2. Sequence Allocation Policy
* **Decision:** The `CUS-xxxxx` sequence is allocated dynamically when a partner is marked with `zconnect_is_customer = True` (either upon initial record creation or subsequent update).
* **Rationale:** Preserves sequence numbering so that standard CRM leads, vendors, and non-logistics contacts do not consume ZConnect customer sequence IDs unnecessarily.
* **Safety:** Safe under concurrent creation via standard `ir.sequence.next_by_code()`. Once generated, the customer code is immutable and indexed.

### 3. Security Role Hierarchy
* **Category:** `Zimbabwe Connect`
* **Roles:**
  * `Customer`: Portal / external shipper role.
  * `Driver`: Delivery operator role.
  * `Dispatcher`: Operations routing and assignment role.
  * `Finance`: Settlement, billing, and invoicing role.
  * `Manager`: Logistics operations manager (inherits Dispatcher & Finance).
  * `Administrator`: Platform super administrator (inherits Manager & System Administration).

---

## Verification & Installation
Install via Odoo Apps list or command line:
```bash
odoo-bin -c odoo.conf -d odoo_enterprise -i zconnect_base --stop-after-init
```
