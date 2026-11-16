// Capture a PNG of a local HTML file with headless Chromium.
// usage: node tools/screenshot.js page.html out.png [width] [maxHeight] [cssSelector]
//   maxHeight    clip the full-page capture to this height (0 = no clip)
//   cssSelector  capture only the first element matching this selector
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const [page, out, width = '1100', maxHeight = '0', selector] = process.argv.slice(2);
  const browser = await chromium.launch();
  const tab = await browser.newPage({ viewport: { width: Number(width), height: 100 }, deviceScaleFactor: 2 });
  await tab.goto('file://' + path.resolve(page));
  if (selector) {
    await tab.locator(selector).first().screenshot({ path: out });
  } else {
    const options = { path: out, fullPage: true };
    if (Number(maxHeight) > 0) options.clip = { x: 0, y: 0, width: Number(width), height: Number(maxHeight) };
    await tab.screenshot(options);
  }
  await browser.close();
})();
