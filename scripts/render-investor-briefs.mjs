import fs from 'node:fs';
import puppeteer from 'puppeteer-core';

const chrome = process.env.CHROME_PATH;
if (!chrome) throw new Error('CHROME_PATH is required');

const jobs = [
  ['docs/source/kopilotti-sales-investor-brief-fi.html', 'docs/kopilotti-sales-asiakas-sijoittajatiivistelma.pdf'],
  ['docs/source/kopilotti-sales-investor-brief-en.html', 'docs/kopilotti-sales-customer-investor-summary.pdf'],
];

const browser = await puppeteer.launch({
  headless: true,
  executablePath: chrome,
  args: ['--no-sandbox', '--disable-dev-shm-usage'],
});

try {
  for (const [source, output] of jobs) {
    const page = await browser.newPage();
    await page.setViewport({ width: 816, height: 1056 });
    await page.setContent(fs.readFileSync(source, 'utf8'), { waitUntil: 'load' });
    const client = await page.createCDPSession();
    const result = await client.send('Page.printToPDF', {
      printBackground: true,
      preferCSSPageSize: true,
      generateTaggedPDF: true,
      generateDocumentOutline: true,
      marginTop: 0,
      marginBottom: 0,
      marginLeft: 0,
      marginRight: 0,
    });
    fs.writeFileSync(output, Buffer.from(result.data, 'base64'));
    await page.close();
  }
} finally {
  await browser.close();
}
