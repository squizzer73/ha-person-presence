import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  rowsForCard,
  ageLabel,
  validateCardConfig,
} from '../../custom_components/person_presence/www/person-presence-card.js';
const state = (person, kind, state, extra = {}) => ({
  state,
  attributes: {
    person_entity_id: person,
    integration: 'person_presence',
    output_kind: kind,
    ...extra,
  },
});
test('state-only discovery respects order and explicit ambiguous choice', () => {
  const states = {
    'sensor.a': state('person.a', 'dashboard_whereabouts', 'Office', {
      freshness: 'current',
    }),
    'sensor.b': state(
      'person.b',
      'dashboard_whereabouts',
      'Park (last known)',
      { freshness: 'last_known', observed_at: '2026-11-06T10:00:00Z' },
    ),
    'sensor.distance': state('person.a', 'distance_from_home', '10', {
      unit_of_measurement: 'm',
    }),
  };
  assert.deepEqual(
    rowsForCard({ states }, { people: ['person.b', 'person.a'] }).map(
      (x) => x.entityId,
    ),
    ['sensor.b', 'sensor.a'],
  );
  assert.equal(rowsForCard({ states }, {})[0].distance.state, '10');
  states['sensor.duplicate'] = state(
    'person.a',
    'dashboard_whereabouts',
    'Elsewhere',
  );
  assert.equal(
    rowsForCard({ states }, {}).find((x) => x.person === 'person.a').ambiguous,
    true,
  );
  assert.equal(
    rowsForCard({ states }, { entities: ['sensor.a'] })[0].ambiguous,
    false,
  );
});
test('unknown unavailable missing hostile labels remain data', () => {
  const states = {
    'sensor.a': state(
      'person.a',
      'dashboard_whereabouts',
      '<img onerror=alert(1)>',
      { freshness: 'last_known' },
    ),
  };
  assert.equal(rowsForCard({ states }, {})[0].value, '<img onerror=alert(1)>');
  assert.equal(
    rowsForCard({ states }, { entities: ['sensor.missing'] })[0].freshness,
    'unknown',
  );
  states['sensor.a'].state = 'unavailable';
  assert.equal(rowsForCard({ states }, {})[0].freshness, 'unknown');
  assert.equal(ageLabel('bad'), 'Age unknown');
  assert.equal(
    ageLabel('2026-11-06T10:00:00Z', Date.parse('2026-11-06T10:05:00Z')),
    '5m ago',
  );
  assert.throws(() => validateCardConfig({ people: 'person.a' }));
  assert.throws(() => validateCardConfig({ entities: ['light.a'] }));
});

test('avatars stay on the HA origin after URL normalization', async () => {
  const { sameOriginPicture } =
    await import('../../custom_components/person_presence/www/person-presence-card.js');
  assert.equal(
    sameOriginPicture('/api/image/avatar', 'https://ha.example'),
    'https://ha.example/api/image/avatar',
  );
  assert.equal(
    sameOriginPicture('/\\external.example/picture', 'https://ha.example'),
    null,
  );
  assert.equal(
    sameOriginPicture('//external.example/picture', 'https://ha.example'),
    null,
  );
});
