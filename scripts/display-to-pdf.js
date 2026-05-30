const fs = require('fs');
const path = require('path');
const XLSX = require('xlsx');
const puppeteer = require('puppeteer');

const INPUT_FILE = path.join(__dirname, '../processed_data/hard_data_exports/hunt_tables/2026/CLEAN_XLXS_STAGED/DISPLAY_READY.xlsx');
const OUTPUT_FILE = path.join(__dirname, '../flipbooks/2026/elk_hunt_tables.pdf');
const outputDir = path.dirname(OUTPUT_FILE);

if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

function generateHTML(rows) {
  return `
  <html>
  <head>
    <style>
      body {
        font-family: Arial;
        font-size: 11px;
        margin: 0;
      }

      h1 {
        text-align: center;
        margin-bottom: 10px;
      }

      table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
      }

      th {
        background: #2f3e2f;
        color: white;
        padding: 6px;
        font-size: 11px;
      }

      td {
        border: 1px solid #ccc;
        padding: 5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      td:nth-child(1),
      td:nth-child(7) {
        white-space: normal;
      }

      tr:nth-child(even) {
        background: #f5f5f5;
      }
    </style>
  </head>

  <body>
    <h1>2026 Utah Elk Hunt Tables</h1>

    <table>
      <thead>
        <tr>
          <th>Hunt Name</th>
          <th>#</th>
          <th>Sex</th>
          <th>Species</th>
          <th>Type</th>
          <th>Weapon</th>
          <th>Season</th>
          <th>Permits / Harvest</th>
          <th>2025 Performance</th>
          <th>Sat</th>
        </tr>
      </thead>

      <tbody>
        ${rows.map(r => `
          <tr>
            <td>${r["HUNT NAME"]}</td>
            <td>${r["HUNT CODE"]}</td>
            <td>${r["SEX"]}</td>
            <td>${r["SPECIES"]}</td>
            <td>${r["TYPE"]}</td>
            <td>${r["WEAPON"]}</td>
            <td>${r["SEASON"]}</td>
            <td>${r["PERMITS / HARVEST"]}</td>
            <td>${r["2025 PERFORMANCE"]}</td>
            <td>${r["SAT"]}</td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  </body>
  </html>
  `;
}

async function run() {
  const workbook = XLSX.readFile(INPUT_FILE);
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const data = XLSX.utils.sheet_to_json(sheet);

  const html = generateHTML(data);

  const browser = await puppeteer.launch();
  const page = await browser.newPage();

  await page.setContent(html, { waitUntil: 'networkidle0' });

  await page.pdf({
    path: OUTPUT_FILE,
    format: 'Letter',
    landscape: true,
    printBackground: true,
    margin: {
      top: '0.4in',
      bottom: '0.4in',
      left: '0.4in',
      right: '0.4in'
    }
  });

  await browser.close();

  console.log("PDF GENERATED:");
  console.log(OUTPUT_FILE);
}

run();