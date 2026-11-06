# Dashboard whereabouts — 0.2.0b2

Added in 0.2.0b2. Earlier versions do not include this sensor.

Use Dashboard whereabouts for a display that retains the last accepted location: Library while current, then Library (last known) when current evidence is insufficient. Its freshness attribute is current, last_known or unknown. Historical values include observed_at (the original accepted observation time), last_known_value and source_entity_id. The observed_at attribute is populated only for last-known fallback; current values do not carry a ticking age attribute. For current observation time, the existing optional Last observation time diagnostic remains available.

Use the original Whereabouts entity and its presence/context attributes for current-location automations. The dashboard entity deliberately preserves history; reading its text alone cannot establish that someone is there now.

One accepted settled observation is stored privately per entry across restarts. The timestamp is never reset to restart/load time. Continuous fresh observations refresh the stored timestamp periodically (at most about once a minute while the place/source are unchanged); a crash can therefore restore a slightly older timestamp. Normal unload/shutdown saves the latest record. Removing the entry removes its history. The legacy last-known diagnostic keeps its previous memory-only behaviour.

An entry with no previously accepted location remains Unknown until a valid observation arrives. The integration does not turn a rejected old provider fix into a remembered person location. Changing the person or removing/remapping the history's source invalidates that record on setup. Historical room labels describe the label at observation time.

For a Markdown dashboard card, replace the fictional entity ID below with your own. HA renders the relative age in the card, so the integration doesn't write age changes into history every minute.

```yaml
type: markdown
content: >-
  {% set entity = 'sensor.alex_comparison_dashboard_whereabouts' %}
  {% set value = states(entity) %}
  {% if value in ['unknown', 'unavailable'] %}
    Alex: location unknown
  {% elif state_attr(entity, 'freshness') == 'last_known' %}
    {% set observed = as_datetime(state_attr(entity, 'observed_at'), none) %}
    Alex: last known at {{ state_attr(entity, 'last_known_value') }}
    {% if observed %}({{ relative_time(observed) }} ago){% endif %}
  {% else %}
    Alex: {{ value }}
  {% endif %}
```
