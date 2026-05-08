const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..');
const sourceDir = 'D:/DOCUMENTS/GitHub/HUNTS/pipeline/raw/hunt_unit_mapping/shape/LOA_2024_gdb_6053011641283393372';
const sourceBase = path.join(sourceDir, 'Utah_Landowner_Association_(LOA)_Boundaries');
const outputPath = path.join(repo, 'processed_data', 'boundaries', 'LO0010.geojson');

const WEB_MERCATOR_RADIUS = 6378137;

function readDbf(filePath) {
  const buffer = fs.readFileSync(filePath);
  const recordCount = buffer.readUInt32LE(4);
  const headerLength = buffer.readUInt16LE(8);
  const recordLength = buffer.readUInt16LE(10);
  const fields = [];
  let offset = 32;
  while (buffer[offset] !== 0x0d && offset < headerLength) {
    const rawName = buffer.subarray(offset, offset + 11).toString('ascii').replace(/\0/g, '').trim();
    const type = String.fromCharCode(buffer[offset + 11]);
    const length = buffer[offset + 16];
    fields.push({ name: rawName, type, length });
    offset += 32;
  }

  const rows = [];
  for (let i = 0; i < recordCount; i += 1) {
    const rowOffset = headerLength + (i * recordLength);
    if (buffer[rowOffset] === 0x2a) continue;
    let cursor = rowOffset + 1;
    const row = {};
    for (const field of fields) {
      const raw = buffer.subarray(cursor, cursor + field.length).toString('latin1').trim();
      row[field.name] = raw;
      cursor += field.length;
    }
    rows.push(row);
  }
  return rows;
}

function webMercatorToLonLat(x, y) {
  const lon = (x / WEB_MERCATOR_RADIUS) * (180 / Math.PI);
  const lat = ((2 * Math.atan(Math.exp(y / WEB_MERCATOR_RADIUS))) - (Math.PI / 2)) * (180 / Math.PI);
  return [Number(lon.toFixed(7)), Number(lat.toFixed(7))];
}

function closeRing(ring) {
  if (!ring.length) return ring;
  const first = ring[0];
  const last = ring[ring.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) ring.push(first);
  return ring;
}

function readShp(filePath) {
  const buffer = fs.readFileSync(filePath);
  const geometries = [];
  let offset = 100;
  while (offset + 8 <= buffer.length) {
    const recordNumber = buffer.readInt32BE(offset);
    const contentLength = buffer.readInt32BE(offset + 4) * 2;
    const contentOffset = offset + 8;
    const shapeType = buffer.readInt32LE(contentOffset);
    if (shapeType === 0) {
      geometries.push(null);
      offset = contentOffset + contentLength;
      continue;
    }
    if (shapeType !== 5 && shapeType !== 15) {
      throw new Error(`Unsupported shape type ${shapeType} in record ${recordNumber}`);
    }
    const numParts = buffer.readInt32LE(contentOffset + 36);
    const numPoints = buffer.readInt32LE(contentOffset + 40);
    const partsOffset = contentOffset + 44;
    const pointsOffset = partsOffset + (numParts * 4);
    const partStarts = [];
    for (let p = 0; p < numParts; p += 1) {
      partStarts.push(buffer.readInt32LE(partsOffset + (p * 4)));
    }
    const points = [];
    for (let p = 0; p < numPoints; p += 1) {
      const pointOffset = pointsOffset + (p * 16);
      points.push(webMercatorToLonLat(buffer.readDoubleLE(pointOffset), buffer.readDoubleLE(pointOffset + 8)));
    }
    const polygons = [];
    for (let p = 0; p < numParts; p += 1) {
      const start = partStarts[p];
      const end = p + 1 < numParts ? partStarts[p + 1] : points.length;
      const ring = closeRing(points.slice(start, end));
      if (ring.length >= 4) polygons.push([ring]);
    }
    geometries.push(polygons.length === 1
      ? { type: 'Polygon', coordinates: polygons[0] }
      : { type: 'MultiPolygon', coordinates: polygons });
    offset = contentOffset + contentLength;
  }
  return geometries;
}

function main() {
  const rows = readDbf(`${sourceBase}.dbf`);
  const geometries = readShp(`${sourceBase}.shp`);
  const features = rows
    .map((row, index) => ({ row, geometry: geometries[index] }))
    .filter(({ row, geometry }) => geometry && /diamond/i.test(row.LOA_Name || '') && String(row.Species || '').toLowerCase() === 'deer')
    .map(({ row, geometry }) => ({
      type: 'Feature',
      properties: {
        hunt_code: 'LO0010',
        boundary_id: '206',
        BoundaryID: '206',
        boundary_name: row.LOA_Name || 'Diamond Mountain LOA',
        Boundary_Name: row.LOA_Name || 'Diamond Mountain LOA',
        loa_name: row.LOA_Name || '',
        acres: row.Acres || '',
        species: row.Species || '',
        hunt_unit: row.Hunt_Unit || '',
        source: 'Utah DWR LOA 2024 shapefile',
      },
      geometry,
    }));

  if (features.length !== 1) {
    throw new Error(`Expected exactly one Diamond Mountain deer LOA feature, found ${features.length}`);
  }

  const geojson = {
    type: 'FeatureCollection',
    metadata: {
      hunt_code: 'LO0010',
      boundary_id: '206',
      member_boundary_ids: [],
      source_boundary_ids: ['206'],
      source_hunt_code: 'LO0010',
      merged_boundary_id: null,
      boundary_geometry_type: 'single_loa_boundary',
      generated_from: 'Utah_Landowner_Association_(LOA)_Boundaries.shp',
      boundary_source_authority: 'Utah DWR',
      boundary_source_file: 'LOA_2024_gdb_6053011641283393372',
    },
    features,
  };

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(geojson, null, 2));
  console.log(JSON.stringify({
    output: outputPath,
    features: features.length,
    boundary_id: '206',
    source: sourceBase,
  }, null, 2));
}

main();
