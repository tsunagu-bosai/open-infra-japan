# My-bottle discount location data attribution

The chain location files in this directory are derived from the existing OpenStreetMap Japan `places-cafe.csv` snapshot. OSM source IDs, original names, addresses, coordinates, and snapshot timestamp are retained per row. The source file was not modified or downloaded again for this export.

- Attribution: © OpenStreetMap contributors — https://www.openstreetmap.org/copyright
- License: Open Database License (ODbL) 1.0 — https://opendatacommons.org/licenses/odbl/1-0/
- Derived location database: offered under ODbL 1.0.
- Source snapshot replication time: 2026-10-25T21:21:21Z.
- Source CSV SHA-256: `c560c779e4f8ca362fd865dad8227f788478a24f32c2f0d5744acabf2702daa3`.

Chain discount rules are independent facts sourced from each chain's official website. Those URLs appear in `mybottle-discount-chain-services.csv` and are not the source of the OSM coordinates. Shop operation status and exact entrance position have not been verified.

The five location files are derived from OSM location data and retain the source IDs for auditability. The chain service catalog is a separate table; location rows link to a shared `service_id` rather than copying policy text.
