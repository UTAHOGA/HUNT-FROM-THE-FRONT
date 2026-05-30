const fs = require('fs');
const path = require('path');
const XLSX = require('xlsx');
const puppeteer = require('puppeteer');

const INPUT_DIR = path.join(__dirname, '../processed_data/hard_data_exports/hunt_tables/2026/CLEAN_XLXS_STAGED');
const OUTPUT_DIR = path.join(__dirname, '../flipbooks/2026');

// ensure output folder exists
if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

function generateHTML(data, title) {
  return `
  <html>
  <head>
    <style>
      body {
        font-family: Arial;
        font-size: 10px;
        padding: 10px;
      }

      h1 {
        text-align: center;
      }

      table {
        width: 100%;
        border-collapse: collapse;
      }

      th {
        background: #2f3e2f;
        color: white;
        padding: 6px;
      }

      td {
        border: 1px solid #ccc;
        padding: 4px;
      }

      tr:nth-child(even) {
        background: #f5f5f5;
      }
    </style>
  </head>

  <body>
    <h1>${title}</h1>

    <table>
      <thead>
        <tr>
          <th>Hunt</th>
          <th>Code</th>
          <th>Weapon</th>
          <th>Season</th>
          <th>Permits / Harvest</th>
          <th>Performance</th>
        </tr>
      </thead>

      <tbody>
        ${data.map(r => {
          const permits = r["2026 PERMITS TOTAL"] || "";
          const harvest = r["2026 HARVEST SUCCESS"] || "";

          const success = r["2026 HARVEST SUCCESS"] || "";
          const age = r["2026 HARVEST AGE"] || "";
          const days = r["2026 HARVEST DAYS"] || "";

          return `
            <tr>
              <td>${r["HUNT NAME"] || ""}</td>
              <td>${r["HUNT CODE"] || ""}</td>
              <td>${r["WEAPON"] || ""}</td>
              <td>${r["SEASON"] || ""}</td>
              <td>${permits} / ${harvest}</td>
              <td>${success}% | ${age}yr | ${days}d</td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
  </body>
  </html>
  `;
}
 function generateHTML(data, title) {
  return `...`;
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
        padding: 5px;
      }

      td {
        border: 1px solid #ccc;
        padding: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      tr:nth-child(even) {
        background: #f5f5f5;
      }

      td:nth-child(1) {
        white-space: normal;
      }
    </style>
  </head>

  <body>
    <h1>${title}</h1>

    <table>
      <thead>
        <tr>
          ${headers.map(h => `<th>${h}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
        ${data.map(row => `
          <tr>
            ${headers.map(h => `<td>${row[h] || ''}</td>`).join('')}
          </tr>
        `).join('')}
      </tbody>
    </table>
  </body>
  </html>
  `;
}

async function run() {
  console.log("STARTING BATCH PDF GENERATION");

  const files = fs.readdirSync(INPUT_DIR).filter(f => f.endsWith('.xlsx'));

  if (files.length === 0) {
    console.log("❌ NO XLSX FILES FOUND");
    return;
  }

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox']
  });

  const page = await browser.newPage();

  for (const file of files) {
    console.log("PROCESSING:", file);

    const filePath = path.join(INPUT_DIR, file);
    const workbook = XLSX.readFile(filePath);

    const sheet = workbook.Sheets[workbook.SheetNames[0]];
    const data = XLSX.utils.sheet_to_json(sheet, { defval: "" });

    if (data.length === 0) {
      console.log("⚠️ SKIPPING EMPTY FILE:", file);
      continue;
    }

    const html = generateHTML(data, file.replace('.xlsx', ''));

    await page.setContent(html, { waitUntil: 'networkidle0' });

    const outputFile = path.join(
      OUTPUT_DIR,
      file.replace('.xlsx', '.pdf')
    );

    await page.pdf({
      path: outputFile,
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

    console.log("✅ CREATED:", outputFile);
  }

  await browser.close();

  console.log("🔥 ALL FILES COMPLETE");
}

run();