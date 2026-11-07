import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const browser = await chromium.launch({ headless: true });
const out = process.env.PRESENCE_ARTIFACT_DIR || 'artifacts';
await fs.mkdir(out, { recursive: true });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  for (const width of [390, 900]) {
    await page.setViewportSize({ width, height: 1050 });
    await page.goto(
      process.env.PRESENCE_FIXTURE_URL ||
        'http://127.0.0.1:8766/tests/frontend/fixture.html',
    );
    await page.locator('person-presence-card button').first().waitFor();
    assert.equal(await page.locator('person-presence-card button').count(), 7);
    assert.equal(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      true,
    );
    await page.getByRole('button', { name: 'River: Study' }).click();
    assert.equal(
      await page.evaluate(() => window.moreInfo),
      'sensor.river_display',
    );
    assert.equal(await page.locator('.badge.last_known').count(), 1);
    assert.equal(await page.locator('.badge.unknown').count(), 1);
    await page.screenshot({
      path: `${out}/family-${width}.png`,
      fullPage: true,
    });
  }
  await page.evaluate(() => {
    const card = document.querySelector('person-presence-card');
    window.fixtureHass.states['sensor.river_display'].state =
      '<img src=x onerror=alert(1)>';
    card.hass = window.fixtureHass;
  });
  assert.equal(await page.locator('person-presence-card img').count(), 0);
  assert.ok(
    (
      await page.locator('person-presence-card .value').allTextContents()
    ).includes('<img src=x onerror=alert(1)>'),
  );
  await page.evaluate(() => {
    const editor = document.createElement('person-presence-card-editor');
    editor.setConfig({ type: 'custom:person-presence-card' });
    document.querySelector('main').append(editor);
    editor.addEventListener(
      'config-changed',
      (e) => (window.editorResult = e.detail.config),
    );
  });
  await page.getByLabel('Title', { exact: true }).fill('Household');
  await page.getByLabel('Title', { exact: true }).dispatchEvent('change');
  assert.equal(
    await page.evaluate(() => window.editorResult.title),
    'Household',
  );
  const title = page.getByLabel('Title', { exact: true });
  await title.fill('Draft title');
  await page.evaluate(() => {
    document.querySelector('person-presence-card-editor').hass =
      window.fixtureHass;
  });
  assert.equal(await title.inputValue(), 'Draft title');
  assert.deepEqual(errors, []);
  console.log(
    'Browser checks passed: 7-person mobile/desktop, stale/unknown, more-info, editor, text escaping; no page errors.',
  );
} finally {
  await browser.close();
}
