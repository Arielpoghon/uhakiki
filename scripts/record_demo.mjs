// Uhakiki demo recording — dashboard flow via Playwright (headless Chromium).
import { chromium } from "playwright-core";
import { execSync } from "node:child_process";

const CHROME = execSync(
  "ls -d ~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome | sort | tail -1",
  { shell: "/bin/bash" },
).toString().trim();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const context = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: "raw", size: { width: 1280, height: 720 } },
});
const page = await context.newPage();

// 1. landing (5s)
await page.goto("http://127.0.0.1:8010/", { waitUntil: "domcontentloaded" });
await sleep(5000);

// 2. ALLOW: clean invoice → screen + attest + explain
await page.click("#run");
await page.waitForTimeout(12000); // verdict + rules + EN/SW + attestation dwell
// scroll to show explanation + attestation
await page.evaluate(() => window.scrollTo({ top: 400, behavior: "smooth" }));
await sleep(5000);
await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
await sleep(2000);

// 3. DENY: flip to sanctioned buyer → run
await page.click("#flip");
await sleep(1200);
await page.click("#run");
await sleep(8000);
await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
await sleep(6000);

// 4. wallet screen
await page.click("#wsc");
await sleep(6000);

await page.waitForTimeout(500);
await context.close(); // flush video
await browser.close();
console.log("record done");
