/* Local Person Presence card. No external libraries or location services. */
export function validateCardConfig(config) {
  if (!config || typeof config !== 'object')
    throw new Error('Card configuration required');
  for (const [key, prefix] of [
    ['people', 'person.'],
    ['entities', 'sensor.'],
  ]) {
    if (
      config[key] !== undefined &&
      (!Array.isArray(config[key]) ||
        config[key].some((x) => typeof x !== 'string' || !x.startsWith(prefix)))
    )
      throw new Error(`${key} must be a list of ${prefix} entities`);
  }
  return { ...config };
}
export function sameOriginPicture(value, origin) {
  if (
    typeof value !== 'string' ||
    !value.startsWith('/') ||
    value.startsWith('//')
  )
    return null;
  try {
    const url = new URL(value, origin);
    return url.origin === origin ? url.href : null;
  } catch {
    return null;
  }
}
export function ageLabel(value, now = Date.now()) {
  const date = typeof value === 'number' ? value * 1000 : Date.parse(value);
  if (!Number.isFinite(date) || date > now) return 'Age unknown';
  const minutes = Math.floor((now - date) / 60000);
  return minutes < 1
    ? 'Just now'
    : minutes < 60
      ? `${minutes}m ago`
      : minutes < 1440
        ? `${Math.floor(minutes / 60)}h ago`
        : `${Math.floor(minutes / 1440)}d ago`;
}
const usable = (s) =>
  s && !['unknown', 'unavailable', 'none', ''].includes(s.state);
export function attributionLinks(place) {
  return usable(place) && place.attributes?.provider === 'geoapify'
    ? [
        { href: 'https://www.geoapify.com/', label: 'Powered by Geoapify' },
        {
          href: 'https://www.openstreetmap.org/copyright',
          label: '© OpenStreetMap contributors',
        },
      ]
    : [];
}
export function rowsForCard(hass, config = {}) {
  const states = hass?.states || {};
  const matches = Object.entries(states).filter(
    ([, s]) =>
      s.attributes?.integration === 'person_presence' &&
      s.attributes.output_kind === 'dashboard_whereabouts',
  );
  const people = config.people?.length
    ? config.people
    : [
        ...new Set(matches.map(([, s]) => s.attributes.person_entity_id)),
      ].sort();
  const chosen = config.entities?.length
    ? config.entities.map((id) => ({
        id,
        person: states[id]?.attributes?.person_entity_id,
      }))
    : people.map((person) => {
        const candidates = matches.filter(
          ([, s]) => s.attributes.person_entity_id === person,
        );
        return {
          id: candidates.length === 1 ? candidates[0][0] : null,
          person,
          ambiguous: candidates.length > 1,
        };
      });
  return chosen.map(({ id, person, ambiguous }) => {
    const s = states[id],
      p = states[person];
    const related = (kind) => {
      const found = Object.values(states).filter(
        (x) =>
          x.attributes?.integration === 'person_presence' &&
          x.attributes.output_kind === kind &&
          x.attributes.person_entity_id === person,
      );
      return found.length === 1 ? found[0] : null;
    };
    return {
      entityId: id,
      person,
      name: p?.attributes?.friendly_name || person || id,
      avatar: p?.attributes?.entity_picture,
      ambiguous: !!ambiguous,
      value: ambiguous
        ? 'Choose a sensor in card settings'
        : usable(s)
          ? s.state
          : 'Unknown',
      freshness: usable(s) ? s.attributes.freshness || 'unknown' : 'unknown',
      observedAt: s?.attributes.observed_at,
      device: s?.attributes.selected_device_name,
      distance: related('distance_from_home'),
      direction: related('travel_direction'),
      place: related('place_description'),
    };
  });
}
const Base = globalThis.HTMLElement || class {};
function element(tag, text, cls) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}
export class PersonPresenceCard extends Base {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }
  setConfig(config) {
    this.config = validateCardConfig(config);
    this.render();
  }
  set hass(hass) {
    this._hass = hass;
    this.render();
  }
  getCardSize() {
    return Math.max(2, rowsForCard(this._hass, this.config).length);
  }
  static getConfigElement() {
    return document.createElement('person-presence-card-editor');
  }
  static getStubConfig() {
    return {
      type: 'custom:person-presence-card',
      title: 'Family',
      show_device: true,
      show_travel: true,
      show_place: true,
    };
  }
  connectedCallback() {
    this.timer = setInterval(() => this.render(), 60000);
  }
  disconnectedCallback() {
    clearInterval(this.timer);
  }
  render() {
    if (!this.shadowRoot || !this.config) return;
    const style = element('style');
    style.textContent = `:host{display:block}ha-card{display:block;padding:16px;color:var(--primary-text-color,#202124);background:var(--ha-card-background,var(--card-background-color,#fff));border-radius:var(--ha-card-border-radius,12px)}h2{font:500 20px var(--paper-font-body1_-_font-family,Arial);margin:0 0 8px}.row{display:flex;align-items:center;gap:12px;width:100%;background:none;color:inherit;border:0;border-top:1px solid var(--divider-color,#ddd);padding:14px 0;text-align:left;font:inherit;cursor:pointer}.row:focus-visible{outline:2px solid var(--primary-color,#03a9f4);outline-offset:3px}.avatar{height:40px;width:40px;flex:0 0 40px;border-radius:50%;object-fit:cover;background:var(--secondary-background-color,#eee);display:grid;place-items:center}.body{min-width:0;flex:1}.name{font-weight:600}.value{margin-top:4px;overflow-wrap:anywhere}.details{font-size:12px;line-height:1.5;color:var(--secondary-text-color,#616161);overflow-wrap:anywhere}.badge{font-size:11px;border:1px solid currentColor;padding:2px 6px;border-radius:10px;white-space:nowrap}.last_known{color:var(--warning-color,#9c6500)}.unknown{color:var(--secondary-text-color,#616161)}.empty{padding:16px 0;font-size:14px}@media(max-width:360px){.row{gap:8px}.badge{white-space:normal;max-width:70px;text-align:center}}`;
    const card = element('ha-card');
    card.append(element('h2', this.config.title || 'Family'));
    const rows = rowsForCard(this._hass, this.config);
    if (!rows.length)
      card.append(
        element(
          'div',
          'No Person Presence sensors found. Add a person or choose sensors in card settings.',
          'empty',
        ),
      );
    for (const row of rows) {
      const button = element('button', undefined, 'row');
      button.type = 'button';
      button.setAttribute('aria-label', `${row.name}: ${row.value}`);
      if (row.entityId)
        button.addEventListener('click', () =>
          this.dispatchEvent(
            new CustomEvent('hass-more-info', {
              detail: { entityId: row.entityId },
              bubbles: true,
              composed: true,
            }),
          ),
        );
      const avatar = element(
        'span',
        (row.name || '?').slice(0, 1).toUpperCase(),
        'avatar',
      );
      // Person pictures only from same-origin HA paths; no externally loaded images.
      const picture = sameOriginPicture(row.avatar, globalThis.location.origin);
      if (picture) {
        const img = element('img', undefined, 'avatar');
        img.src = picture;
        img.alt = '';
        button.append(img);
      } else button.append(avatar);
      const body = element('div', undefined, 'body');
      body.append(
        element('div', row.name, 'name'),
        element('div', row.value, 'value'),
      );
      const details = [];
      if (row.freshness === 'last_known')
        details.push(ageLabel(row.observedAt));
      if (this.config.show_device !== false && row.device)
        details.push(`Following ${row.device}`);
      if (
        this.config.show_travel !== false &&
        row.freshness === 'current' &&
        usable(row.distance)
      )
        details.push(
          `${row.distance.state} ${row.distance.attributes.unit_of_measurement || 'm'} from home`,
        );
      if (
        this.config.show_travel !== false &&
        row.freshness === 'current' &&
        usable(row.direction)
      )
        details.push(row.direction.state.replaceAll('_', ' '));
      if (
        this.config.show_place !== false &&
        row.freshness === 'current' &&
        usable(row.place)
      ) {
        details.push(`Approximate place: ${row.place.state}`);
        if (row.place.attributes.attribution)
          details.push(row.place.attributes.attribution);
      }
      if (details.length)
        body.append(element('div', details.join(' · '), 'details'));
      button.append(
        body,
        element(
          'span',
          row.freshness === 'current'
            ? 'Current'
            : row.freshness === 'last_known'
              ? 'Last known'
              : 'Unknown',
          `badge ${row.freshness}`,
        ),
      );
      card.append(button);
      if (this.config.show_place !== false && row.freshness === 'current') {
        const links = attributionLinks(row.place);
        if (links.length) {
          const attribution = element('div', undefined, 'details attribution');
          attribution.style.cssText = 'padding:0 0 12px 52px';
          for (const [index, item] of links.entries()) {
            if (index) attribution.append(document.createTextNode(' · '));
            const link = element('a', item.label);
            link.href = item.href;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.style.color = 'var(--primary-color,#03a9f4)';
            attribution.append(link);
          }
          card.append(attribution);
        }
      }
    }
    this.shadowRoot.replaceChildren(style, card);
  }
}
export class PersonPresenceEditor extends Base {
  setConfig(config) {
    this.config = { ...config };
    this.render();
  }
  set hass(hass) {
    this._hass = hass;
  }
  connectedCallback() {
    this.render();
  }
  render() {
    if (!this.config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' });
    const root = element('div');
    for (const [key, label] of [
      ['title', 'Title'],
      ['people', 'Person entities in display order (comma-separated)'],
      ['entities', 'Explicit dashboard sensors (optional, overrides people)'],
    ]) {
      const field = element('label', label);
      field.style.cssText = 'display:block;margin:12px 0';
      const input = element('input');
      input.style.cssText = 'display:block;width:95%;padding:8px';
      input.value = Array.isArray(this.config[key])
        ? this.config[key].join(', ')
        : this.config[key] || '';
      input.addEventListener('change', () => {
        const value =
          key === 'title'
            ? input.value
            : input.value
                .split(',')
                .map((x) => x.trim())
                .filter(Boolean);
        const next = { ...this.config, [key]: value };
        try {
          validateCardConfig(next);
          input.setCustomValidity('');
          this.config = next;
          this.fire();
        } catch (e) {
          input.setCustomValidity(e.message);
          input.reportValidity();
        }
      });
      field.append(input);
      root.append(field);
    }
    for (const [key, label] of [
      ['show_device', 'Show selected device'],
      ['show_travel', 'Show distance and direction'],
      ['show_place', 'Show approximate place'],
    ]) {
      const field = element('label', label);
      field.style.cssText = 'display:block;margin:12px 0';
      const input = element('input');
      input.type = 'checkbox';
      input.checked = this.config[key] !== false;
      input.addEventListener('change', () => {
        this.config = { ...this.config, [key]: input.checked };
        this.fire();
      });
      field.prepend(input);
      root.append(field);
    }
    this.shadowRoot.replaceChildren(root);
  }
  fire() {
    this.dispatchEvent(
      new CustomEvent('config-changed', {
        detail: { config: this.config },
        bubbles: true,
        composed: true,
      }),
    );
  }
}
if (globalThis.customElements) {
  if (!customElements.get('person-presence-card'))
    customElements.define('person-presence-card', PersonPresenceCard);
  if (!customElements.get('person-presence-card-editor'))
    customElements.define('person-presence-card-editor', PersonPresenceEditor);
  globalThis.customCards = globalThis.customCards || [];
  if (!globalThis.customCards.some((c) => c.type === 'person-presence-card'))
    globalThis.customCards.push({
      type: 'person-presence-card',
      name: 'Person Presence',
      description: 'Family whereabouts with current and last-known locations',
      preview: true,
    });
}
