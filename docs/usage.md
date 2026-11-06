# Using Whereabouts

Choose the Whereabouts entity from the entity picker on a standard Entities or Tile card. Replace example IDs below with your own.

A notification template that handles unknown:

```jinja
{% set place = states('sensor.alex_person_presence_whereabouts') %}
{{ 'Alex: location unknown' if place in ['unknown', 'unavailable'] else 'Alex is in ' ~ place }}
```

For automations, use the stable presence/context attributes and canonical area/zone IDs rather than interpreting arbitrary place labels. This prevents a room called Woods being confused with a zone called Woods.

```yaml
condition: template
value_template: >-
  {{ state_attr('sensor.alex_person_presence_whereabouts', 'presence') == 'home'
     and state_attr('sensor.alex_person_presence_whereabouts', 'context') == 'room'
     and state_attr('sensor.alex_person_presence_whereabouts', 'area_id') == 'library' }}
```

Unknown is not Away. A transition to Unknown must not be treated as a verified departure. The optional tracker stays disabled until you deliberately enable it. If you later attach it to Person, review the other Person trackers: a separate device left at home can still influence HA's built-in selection.
