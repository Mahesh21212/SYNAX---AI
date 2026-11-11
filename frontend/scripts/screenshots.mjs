/**
 * Capture README screenshots from the running app.
 *
 *   node scripts/screenshots.mjs [http://localhost:3000]
 *
 * Requires the API and web client to be running, and at least one seeded
 * conversation (see backend/scripts/seed_demo.py).
 */

import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = process.argv[2] ?? 'http://localhost:3000';
const here = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(here, '..', '..', 'docs', 'screenshots');

const shots = [];

async function main() {
  await mkdir(outDir, { recursive: true });

  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    colorScheme: 'dark',
  });

  // --- 1. Empty state -----------------------------------------------------
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${outDir}/01-empty.png` });
  shots.push('01-empty.png');

  // --- 2. Conversation with a rendered answer ----------------------------
  const conversation = page.getByRole('button', {
    name: /Multi-agent vs single-prompt/i,
  });
  if (await conversation.count()) {
    await conversation.first().click();
    await page.waitForTimeout(700);

    // The app auto-scrolls to the newest message; capture the top of the
    // answer for shot 02, then the tail for shot 03.
    await page.evaluate(() => {
      const transcript = document.querySelector('.flex-1.overflow-y-auto.px-4.py-6');
      if (transcript) transcript.scrollTop = 0;
    });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${outDir}/02-answer.png` });
    shots.push('02-answer.png');

    // Scrolled to the end of the answer, inside the transcript container.
    await page.evaluate(() => {
      const transcript = document.querySelector('.flex-1.overflow-y-auto.px-4.py-6');
      if (transcript) transcript.scrollTop = transcript.scrollHeight;
    });
    await page.waitForTimeout(600);
    await page.screenshot({ path: `${outDir}/03-answer-scrolled.png` });
    shots.push('03-answer-scrolled.png');
  }

  // --- 4. Documents panel -------------------------------------------------
  await page.getByRole('button', { name: 'Documents' }).click();
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${outDir}/04-documents.png` });
  shots.push('04-documents.png');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  // --- 5. Memory panel ----------------------------------------------------
  await page.getByRole('button', { name: 'Memory' }).click();
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${outDir}/05-memory.png` });
  shots.push('05-memory.png');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  // --- 6. Model picker ----------------------------------------------------
  await page.getByRole('button', { name: /Claude|GPT|Gemini|Llama|Mistral|DeepSeek/i })
    .first()
    .click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${outDir}/06-models.png` });
  shots.push('06-models.png');

  await browser.close();
  console.log(`captured ${shots.length} screenshots into ${outDir}`);
  for (const shot of shots) console.log(`  - ${shot}`);
}

main().catch((error) => {
  console.error('screenshot run failed:', error.message);
  process.exit(1);
});
