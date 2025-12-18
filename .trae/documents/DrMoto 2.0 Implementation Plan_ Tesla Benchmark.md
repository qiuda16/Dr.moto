# DrMoto 2.0: Tesla-Benchmark Implementation Plan

To build a fully benchmarked "Tesla App" experience, we will upgrade the DrMoto architecture to support real-time telemetry, remote control, and geospatial services.

## Phase 1: Data Architecture & Telemetry (The Foundation)
**Goal:** Establish the database schema for real-time vehicle status (Step 2 of your request).

1.  **Odoo Backend Upgrade (`drmoto_telemetry` module)**
    *   **Vehicle State Model**: Create `drmoto.vehicle.state` to store dynamic data:
        *   `battery_level` (%), `range_km` (est)
        *   `odometer_km`
        *   `tire_pressure` (FL, FR, RL, RR)
        *   `location` (Lat/Lon)
        *   `locked` (Boolean), `windows_state` (Open/Closed)
        *   `climate_state` (Temp, On/Off)
    *   **Charging Network Model**: Create `drmoto.charging.station` with location, stall availability, and pricing.

2.  **BFF Layer Expansion**
    *   **Sync API**: `GET /vehicle/{id}/state` - Aggregates static info (Model) + dynamic info (State).
    *   **Simulation Engine**: Since we lack real hardware, implement a background task in BFF to simulate battery drain while driving and charging status.

## Phase 2: Core Vehicle Controls (Step 3 & 4)
**Goal:** Implement the "Remote Control" experience.

1.  **Control APIs (`control_api`)**
    *   `POST /vehicle/{id}/command/lock` & `unlock`
    *   `POST /vehicle/{id}/command/climate` (Set Temp, On/Off)
    *   `POST /vehicle/{id}/command/flash_lights` & `honk`
    *   *Implementation*: These will update the Odoo `vehicle.state` and return success/failure to the UI.

2.  **Frontend Interactive Control Panel**
    *   **Visual Controller**: Upgrade the Home View to visualize state (e.g., closed lock icon, headlight animation).
    *   **Climate Screen**: A dedicated circular dial interface for temperature setting.
    *   **Controls Screen**: Quick actions grid (Frunk, Trunk, Vent, Charge Port).

## Phase 3: Location & Charging (Step 3 & 4)
**Goal:** Map integration and charging management.

1.  **Map Integration**: Integrate a map component (Leaflet/OpenStreetMap for global, or Amap for China).
2.  **Location Services**:
    *   Show "My Car" pin on map.
    *   Show "Nearby Superchargers" (from `drmoto.charging.station`).
3.  **Trip Planner**: Simple route drawing from Car Location to selected Charger.

## Phase 4: Service & Maintenance (Refinement)
**Goal:** Polish the existing Service Booking to match Tesla's standards.

1.  **Smart Scheduling**: Calendar-based slot selection (checking Technician availability in Odoo).
2.  **Service Status Tracking**: Detailed timeline (Draft -> Parts Ordered -> In Repair -> Ready).

## Phase 5: Testing & Deployment (Step 5 & 6)
1.  **Automated Testing**: Unit tests for BFF Control APIs.
2.  **Deployment**: Update `docker-compose` to include the new Telemetry services.

---

### Immediate Next Step: Phase 1 & 2 Execution
I will begin by creating the **Odoo Telemetry Models** and the **BFF Control APIs**, then connect them to the **Frontend Home View**. This will give you the "Remote Control" feeling immediately.
