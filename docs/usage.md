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

## Easy optional place lookup

Core tracking works without an account or key. Lookup stays off until enabled.

1. Configure a person under **Settings → Devices & services → Person Presence** and choose **Place lookup**.
2. Select **Configure shared service → Geoapify** and enter your own key from [Geoapify](https://myprojects.geoapify.com/).
3. Choose **Test connection** or **Skip**, then finish and **Save**. The service is shared; enable lookup separately for each person.

Nothing changes until Save. Testing sends a fixed public example coordinate in Berlin and may use one credit. Enabled lookup sends fresh accepted outdoor coordinates rounded to four decimal places. Zones and rooms retain priority; labels never change tracking decisions.

Enter keys only in the masked Home Assistant form. Blank keeps the saved key; explicit removal clears the household service. Private Home Assistant configuration storage is not encrypted, so protect backups. If another editor changes the service, reopen Place lookup to review it before saving.

The family card includes Geoapify/OpenStreetMap attribution. Your account's [pricing and limits](https://www.geoapify.com/pricing/) apply. Advanced authorized or self-hosted Nominatim-compatible services remain supported. Existing custom settings continue until an explicit shared-service change.
