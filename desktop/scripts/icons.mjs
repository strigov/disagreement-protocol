import { deflateSync } from 'node:zlib';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let i = 0; i < 8; i++) crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const name = Buffer.from(type), size = Buffer.alloc(4), crc = Buffer.alloc(4);
  size.writeUInt32BE(data.length); crc.writeUInt32BE(crc32(Buffer.concat([name, data])));
  return Buffer.concat([size, name, data, crc]);
}
function png(size) {
  const rgba = Buffer.alloc((size * 4 + 1) * size);
  const rounded = (x, y, left, top, width, height, radius) => {
    const dx = Math.max(left + radius - x, 0, x - (left + width - radius));
    const dy = Math.max(top + radius - y, 0, y - (top + height - radius));
    return x >= left && x <= left + width && y >= top && y <= top + height && dx * dx + dy * dy <= radius * radius;
  };
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const u = x / size, v = y / size;
    let color = [0, 0, 0, 0];
    if (rounded(u, v, .06, .06, .88, .88, .2)) color = [45, 87, 202, 255];
    if (rounded(u, v, .28, .20, .44, .60, .04)) color = [255, 255, 255, 255];
    if (u > .57 && u < .72 && v > .20 && v < .35 && u - .57 > v - .20) color = [45, 87, 202, 255];
    for (const top of [.43, .53, .63]) if (rounded(u, v, .36, top, .28, .03, .012)) color = [45, 87, 202, 255];
    const offset = y * (size * 4 + 1) + 1 + x * 4;
    for (let channel = 0; channel < 4; channel++) rgba[offset + channel] = color[channel];
  }
  const header = Buffer.alloc(13);
  header.writeUInt32BE(size); header.writeUInt32BE(size, 4); header[8] = 8; header[9] = 6;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', header), chunk('IDAT', deflateSync(rgba)), chunk('IEND', Buffer.alloc(0))]);
}
export async function createIcons(directory) {
  const large = png(1024), small = png(256);
  const icns = Buffer.alloc(16);
  icns.write('icns'); icns.writeUInt32BE(large.length + 16, 4);
  icns.write('ic10', 8); icns.writeUInt32BE(large.length + 8, 12);
  const ico = Buffer.alloc(22);
  ico.writeUInt16LE(1, 2); ico.writeUInt16LE(1, 4);
  ico.writeUInt16LE(1, 10); ico.writeUInt16LE(32, 12);
  ico.writeUInt32LE(small.length, 14); ico.writeUInt32LE(22, 18);
  await Promise.all([
    writeFile(path.join(directory, 'icon.png'), large),
    writeFile(path.join(directory, 'icon.icns'), Buffer.concat([icns, large])),
    writeFile(path.join(directory, 'icon.ico'), Buffer.concat([ico, small])),
  ]);
}
