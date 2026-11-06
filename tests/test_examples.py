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


async def exercise_dashboard_template(test):
    from datetime import timedelta

    from homeassistant.util import dt as dt_util

    text = (Path(__file__).parents[1] / "docs/dashboard-history.md").read_text()
    card = yaml.safe_load(re.search(r"```yaml\n(.*?)\n```", text, re.S).group(1))
    entity = "sensor.alex_comparison_dashboard_whereabouts"
    for value, attrs, expected in [
        ("Library", {"freshness": "current"}, "Alex: Library"),
        (
            "Library (last known)",
            {
                "freshness": "last_known",
                "last_known_value": "Library",
                "observed_at": (dt_util.utcnow() - timedelta(minutes=30)).isoformat(),
            },
            "Alex: last known at Library",
        ),
        ("unknown", {}, "Alex: location unknown"),
        ("unavailable", {}, "Alex: location unknown"),
    ]:
        test.hass.states.async_set(entity, value, attrs)
        rendered = Template(card["content"], test.hass).async_render(parse_result=False)
        test.assertIn(expected, rendered)
        if attrs.get("freshness") == "last_known":
            test.assertIn("ago", rendered)
