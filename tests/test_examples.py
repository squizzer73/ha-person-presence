"""Execute the shipped examples against fictional HA states, including unknown."""

import re
from pathlib import Path

import yaml
from homeassistant.helpers.template import Template


async def exercise_documented_templates(test):
    text = (Path(__file__).parents[1] / "docs/usage.md").read_text()
    notification = re.search(r"```jinja\n(.*?)\n```", text, re.S).group(1)
    for value, expected in [
        ("Library", "Alex is in Library"),
        ("unknown", "Alex: location unknown"),
        ("unavailable", "Alex: location unknown"),
    ]:
        test.hass.states.async_set("sensor.alex_person_presence_whereabouts", value)
        test.assertEqual(
            Template(notification, test.hass).async_render(parse_result=False).strip(),
            expected,
        )
    automation = yaml.safe_load(re.search(r"```yaml\n(.*?)\n```", text, re.S).group(1))
    for attrs, expected in [
        ({"presence": "home", "context": "room", "area_id": "library"}, True),
        ({"presence": "away", "context": "zone", "zone_id": "zone.library"}, False),
        ({}, False),
    ]:
        test.hass.states.async_set(
            "sensor.alex_person_presence_whereabouts", "Library", attrs
        )
        test.assertEqual(
            Template(automation["value_template"], test.hass).async_render(), expected
        )
