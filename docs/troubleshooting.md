# Troubleshooting

- **Unknown:** open Decision and source evidence, or use the unsaved configuration preview. Check actual observation time, availability, accuracy and eligibility; increasing maximum age trades freshness for coverage.
- **Wrong room:** compare the source room sensor and local tracker first. Radio estimates and device placement must be physically tested.
- **Watch left on a table:** without a worn sensor, device preference cannot prove it is on a wrist. A working charging/worn sensor can exclude it; not charging is insufficient.
- **Old iCloud fix despite recent update:** the provider republished an old measurement. The integration will not refresh its age from the HA write time.
- **Source renamed/deleted:** use Configure → Edit device and remap the source. Multiple missing devices can be repaired one at a time before Save. Temporary stale GPS and normal away BLE do not create Repairs.
- **Unsupported source absent from selectors:** use advanced manual mapping, verify its semantics in preview, and do not assume a generic device_tracker provides outdoor coordinates.
- **Last observation diagnostic not changing:** when enabled, the timestamp diagnostic updates independently when a newer accepted observation arrives. The primary and legacy sensors do not publish age-only changes. Current age is also available in preview rather than stored as a live counter.

Download the integration's diagnostics for support only after reviewing the output. The integration-owned payload includes aliases, settings and reason codes, not raw location payloads or household names. HA adds its own system/integration metadata around that payload, so review the full file before sharing. See privacy.md.

- **Charging status expires between iCloud3 updates (b3 candidate):** use automatic charging age or set a bounded custom age in device rules to suit the provider cadence. Automatic iCloud3 limits are 30 minutes for wearables and 150 for other devices, or the shared signal limit if longer; other providers keep the shared limit. This does not refresh the original charging observation or extend wearing/GPS/room/local-guard ages. Expired or unavailable required signals still exclude the device.
