// Head 2 defense doc (layout and rules: docs/documents/HEAD-DOC-TEMPLATE.md).
// Usage: node head2-defense.js  (from this folder; writes ../Head-2-Setup-and-storage.docx)
// Graphs come from figures/ (redraw them first: uv run docs/documents/source/figures/vector_sweep.py).
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  AlignmentType, WidthType, ShadingType, BorderStyle, LevelFormat, PageBreak,
  Footer, PageNumber, HeadingLevel, VerticalAlign, TableLayoutType
} = require('docx');

const FIGURES = path.join(__dirname, 'figures');

const W = 9638; // A4 content width with 2 cm margins
const FONT = 'Arial';
const MONO = 'Consolas';
const C = {
  ink: '17202A', muted: '5B6875', line: 'D3DBE2', accent: '1F5F8B', accentSoft: 'E3EEF6',
  ok: '1D7A4C', okSoft: 'E1F2E8', warn: '8A5700', warnSoft: 'FBF0D9', bad: 'B0362B', badSoft: 'F9E3E0',
  head: 'F1F4F7'
};

// ---------- inline markup: **bold**, `code` ----------
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith('**')) out.push(new TextRun({ text: t.slice(2, -2), ...base, bold: true }));
    else out.push(new TextRun({ text: t.slice(1, -1), ...base, font: MONO, size: (base.size || 21) - 2 }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (text, o = {}) => new Paragraph({
  children: Array.isArray(text) ? text : runs(text, o.run || {}),
  spacing: { before: o.before ?? 0, after: o.after ?? 120, line: o.line ?? 276 },
  alignment: o.align, keepNext: o.keepNext, indent: o.indent,
  border: o.border,
});
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const LABEL = (t, o = {}) => new Paragraph({
  children: [new TextRun({ text: t.toUpperCase(), bold: true, size: 16, color: C.muted, characterSpacing: 20 })],
  spacing: { before: o.before ?? 200, after: 80 }, keepNext: true,
});
const BREAK = () => new Paragraph({ children: [new PageBreak()] });
const bullet = (t, lvl = 0) => new Paragraph({ children: runs(t), numbering: { reference: 'bul', level: lvl }, spacing: { after: 60, line: 276 } });
const SRC = (t) => new Paragraph({
  children: [new TextRun({ text: 'Source: ', size: 16, color: C.muted, bold: true }), new TextRun({ text: t, font: MONO, size: 16, color: C.muted })],
  spacing: { before: 60, after: 200 },
});

const STATUS = {
  Answered: [C.ok, C.okSoft], Partly: [C.warn, C.warnSoft], Open: [C.bad, C.badSoft], Done: [C.ok, C.okSoft],
};
const chip = (s) => new TextRun({ text: ` ${s.toUpperCase()} `, bold: true, size: 15, color: STATUS[s][0], shading: { type: ShadingType.CLEAR, fill: STATUS[s][1], color: 'auto' } });

// ---------- tables ----------
const NB = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
const thin = (c = C.line) => ({ style: BorderStyle.SINGLE, size: 4, color: c });
function cell(content, width, o = {}) {
  let children;
  if (Array.isArray(content) && content.length && (content[0] instanceof Paragraph || content[0] instanceof Table)) children = content;
  else if (Array.isArray(content)) children = [new Paragraph({ children: content, spacing: { after: 0, line: 264 }, alignment: o.align, keepNext: o.keep })];
  else children = String(content).split('\n').map((line) => new Paragraph({
    children: runs(line, { size: o.size || 19, bold: o.bold, color: o.color }),
    spacing: { after: 40, line: 264 }, alignment: o.align, keepNext: o.keep,
  }));
  return new TableCell({
    children, width: { size: width, type: WidthType.DXA },
    shading: o.fill ? { type: ShadingType.CLEAR, fill: o.fill, color: 'auto' } : undefined,
    margins: { top: o.pad ?? 80, bottom: o.pad ?? 80, left: 110, right: 110 },
    verticalAlign: o.valign || VerticalAlign.TOP,
    columnSpan: o.span,
    borders: o.borders || { top: thin(), bottom: thin(), left: thin(), right: thin() },
  });
}
// grid table: header row + body rows (arrays of strings)
function grid(widths, header, rows, o = {}) {
  const tr = [];
  if (header) tr.push(new TableRow({ tableHeader: true, cantSplit: true, children: header.map((h, i) => cell(h, widths[i], { fill: C.head, bold: true, size: 17, color: C.ink, keep: true })) }));
  rows.forEach((r, ri) => tr.push(new TableRow({ cantSplit: true, children: r.map((v, i) => {
    const hl = o.highlight && o.highlight(r, i);
    return cell(v, widths[i], { keep: rows.length <= 12 && ri < rows.length - 1, fill: hl ? C.accentSoft : (o.firstColFill && i === 0 ? 'FAFBFC' : undefined), bold: o.firstColBold && i === 0, align: o.align && o.align[i] });
  }) })));
  return new Table({ width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths, rows: tr, layout: TableLayoutType.FIXED });
}

// ======================================================================
// CONTENT
// ======================================================================
const body = [];

// A repo graph at text width, keeping its own shape (the PNG header holds its size), and its caption.
function figure(name, caption) {
  const data = fs.readFileSync(path.join(FIGURES, name));
  const width = 620, height = Math.round(width * data.readUInt32BE(20) / data.readUInt32BE(16));
  body.push(new Paragraph({ children: [new ImageRun({ type: 'png', data, transformation: { width, height } })], spacing: { before: 160, after: 60 }, alignment: AlignmentType.CENTER, keepNext: true }));
  body.push(P(caption, { run: { size: 18, color: C.muted } }));
}

// ---------- cover ----------
body.push(P([new TextRun({ text: 'EYKON  ·  DEFENSE NOTES  ·  HEAD 2 OF THE PIPELINE', bold: true, size: 16, color: C.accent, characterSpacing: 30 })], { after: 80 }));
body.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun('Setup & storage')] }));
body.push(P('Where the vectors live, how the tables are shaped, and the ground rules that keep the laptop and the phone in step.', { run: { color: C.muted, size: 22 }, after: 200 }));

body.push(grid([2100, W - 2100], null, [
  ['**Last updated**', '7 Nov 2026'],
  ['**Overall status**', 'Built and in the app. Re-tested on two phones with real vectors; the failure confirmed on a third phone, and the setup reproduced on a second laptop. Memory limit found; plan for it still open.'],
  ['**Cards**', 'EYKO-1 (tables), EYKO-31 (storage test), EYKO-30 (pytest), EYKO-90 (size sweep), EYKO-100 (full test), EYKO-102 (faster search in app), EYKO-94 (three-phone proof pack), EYKO-92 (clean clone), EYKO-84 (second phone, whole pipeline)'],
], { firstColFill: true }));

body.push(LABEL('How to use this document', { before: 240 }));
body.push(grid([2400, W - 2400], null, [
  ['**Part A · The card**', '2-minute refresh. Read this the night before.'],
  ['**Part B · The story**', 'How the work went, step by step. Use it to explain the Head out loud.'],
  ['**Part C · Hard questions**', 'What a strict examiner will ask, what to say, and what to show.'],
  ['**Part D · Evidence**', 'The tables and graphs to put in front of the professor. Every claim in A–C points here (E1, E2 …).'],
  ['**Part E · Words & gaps**', 'Plain meanings of the technical words, the open gaps, and how to update this doc.'],
], { firstColFill: true }));

// ======================================================================
// PART A
// ======================================================================
body.push(BREAK());
body.push(H1('Part A · The card'));

body.push(LABEL('In one breath', { before: 80 }));
body.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: [W], layout: TableLayoutType.FIXED,
  rows: [new TableRow({ children: [cell([
    P('Everything the app remembers lives in **one SQLite file** on the phone. We planned to use a vector plugin (sqlite-vec), but **Android blocks every SQLite plugin**, so we store vectors as plain bytes (BLOBs), load them into memory once, and compare the query against every one of them. That is fast enough. **Memory, not speed, is now the limit.**', { run: { size: 23 }, after: 0, line: 300 }),
  ], W, { fill: C.accentSoft, pad: 160, borders: { top: NB, bottom: NB, right: NB, left: { style: BorderStyle.SINGLE, size: 24, color: C.accent } } })] })],
}));

body.push(LABEL('Where it sits in the pipeline'));
const stages = ['Record video', 'Job queue', 'Frames: split, filter, dedup', 'Scene: objects, place, action', 'Vectors: image + text', 'Search'];
const sw = Math.floor(W / stages.length);
const swArr = stages.map((_, i) => (i === stages.length - 1 ? W - sw * (stages.length - 1) : sw));
body.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: swArr, layout: TableLayoutType.FIXED,
  rows: [
    new TableRow({ children: stages.map((s, i) => cell([new TextRun({ text: (i ? '→ ' : '') + s, size: 17, bold: true })], swArr[i], { align: AlignmentType.CENTER, valign: VerticalAlign.CENTER })) }),
    new TableRow({ children: [cell([new TextRun({ text: 'HEAD 2 · one SQLite database that every stage above writes into and reads from', bold: true, size: 18, color: 'FFFFFF' })], W, { span: stages.length, fill: C.accent, align: AlignmentType.CENTER, borders: { top: NB, bottom: NB, left: NB, right: NB } })] }),
  ],
}));
body.push(P('It comes first because every later stage depends on it. Nothing feeds into it; everything builds on it.', { run: { size: 19, color: C.muted }, before: 80 }));

body.push(LABEL('What · Why · Result'));
const t3 = Math.floor(W / 3);
body.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: [t3, t3, W - 2 * t3], layout: TableLayoutType.FIXED,
  rows: [
    new TableRow({ children: ['What we did', 'Why', 'Result'].map((h, i) => cell(h, i < 2 ? t3 : W - 2 * t3, { fill: C.head, bold: true, size: 18 })) }),
    new TableRow({ children: [
      cell('Tested sqlite-vec on real phones. It failed, so we used plain byte columns searched in memory. One table design, shared by laptop and phone, with raw SQL.', t3),
      cell('The database shape had to be fixed before anything else could be built. Same design and same SQL on both sides means laptop experiments carry over to the phone.', t3),
      cell('The app\'s whole search: **302 ms** for 20k frames on the cheap phone (was 1.3 s), same results. All three vector tables fit up to 20k rows each and run out of memory at 50k.', W - 2 * t3),
    ] }),
  ],
}));

body.push(LABEL('Numbers to remember'));
const nums = [
  ['302 ms', 'the app\'s whole search, 20k frames, cheap phone (A32). Was 1.3 s.', 'E6 · Head 7'],
  ['4.3×', 'faster app search after fixing our own code. 2,400 of 2,400 hits identical.', 'E6, E7 · Head 7'],
  ['268 MB', 'memory Android gives the app. The real ceiling.', 'E8'],
  ['20k ✓  50k ✗', 'rows per table that fit with all three tables loaded', 'E8'],
];
const nw = Math.floor(W / 4);
const nwArr = [nw, nw, nw, W - 3 * nw];
body.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: nwArr, layout: TableLayoutType.FIXED,
  rows: [new TableRow({ children: nums.map((n, i) => cell([
    new Paragraph({ children: [new TextRun({ text: n[0], bold: true, size: 30, color: C.accent })], spacing: { after: 60 } }),
    new Paragraph({ children: [new TextRun({ text: n[1], size: 17 })], spacing: { after: 60, line: 252 } }),
    new Paragraph({ children: [new TextRun({ text: 'Show: ' + n[2], size: 15, color: C.muted, bold: true })], spacing: { after: 0 } }),
  ], nwArr[i], { pad: 120 })) })],
}));

body.push(LABEL('Decisions and the reason for each'));
body.push(grid([3700, 4338, 1600], ['Decision', 'Because', 'Show'], [
  ['Vectors are float32 BLOBs, loaded into memory once, searched by dot product. No sqlite-vec.', 'sqlite-vec does not load on Android. BLOBs in memory took 81 ms at 20k on the cheap phone; reading them from SQLite on every search took 1.4 s.', 'E2, E4, E5'],
  ['`src/video_memory/schema.py` is the single table design; the phone copies it.', 'One design in two languages, so they cannot drift apart.', 'E9'],
  ['Raw SQL, no ORM (no Room entities).', 'The same SQL statements run on the laptop and the phone.', 'E1'],
  ['pytest as the laptop test runner (EYKO-30).', 'One runner: `task test`, `task smoke`.', '—'],
  ['AGPL / research-only models allowed while academic.', 'Needed for YOLOE (Head 5). Must be re-decided before any release.', '—'],
]));

body.push(LABEL('Weak spots: say these before they find them'));
const weak = [
  ['Open', 'Never tried shipping our own SQLite, the only way left to run sqlite-vec on Android (EYKO-93).'],
  ['Open', 'No chosen plan yet for libraries past 20k–50k frames (EYKO-98).'],
  ['Partly', 'The 200 ms pass mark and the "1 hour of video a day" estimate have no source yet (EYKO-101).'],
  ['Open', 'Hot phone and low battery not measured; runs were on phones plugged in by cable (EYKO-95).'],
  ['Partly', 'The whole search in the app is still 302 ms on the cheap phone at 20k, and the first search after opening takes 2.0 s.'],
];
body.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: [1300, W - 1300], layout: TableLayoutType.FIXED,
  // keep: the block moves to the next page as a whole instead of leaving a few rows behind
  rows: weak.map(([s, t], i) => new TableRow({ cantSplit: true, children: [
    cell([chip(s)], 1300, { keep: i < weak.length - 1, borders: { top: NB, left: NB, right: NB, bottom: thin() } }),
    cell(t, W - 1300, { keep: i < weak.length - 1, borders: { top: NB, left: NB, right: NB, bottom: thin() } }),
  ] })),
}));

// ======================================================================
// PART B
// ======================================================================
body.push(BREAK());
body.push(H1('Part B · The story'));
body.push(P('How the work actually went, in order. Each step is one thing that happened, with the evidence to point at.', { run: { color: C.muted } }));

const steps = [
  ['Question', null, 'Where do the vectors live?', 'Every kept frame becomes 512 numbers (image vector) and every caption 384 numbers (text vector). Every later stage reads and writes them, so this had to be settled first.', null],
  ['Rule set before testing', null, 'Pass mark fixed in advance', 'Plan: use sqlite-vec. If it fails on a phone, fall back to plain BLOBs, but only if one search takes **under 200 ms for 20,000 vectors on the slow phone**. The 200 ms was our own target (no source yet: EYKO-101). Fixing the bar first means the result cannot be argued into a decision afterwards.', null],
  ['Test · 12 Oct · EYKO-31', 'bad', 'sqlite-vec failed on the phone', 'On the Samsung A32: "no such module: vec0". It worked on the laptop (31 ms at 20k), but not on Android.', 'E2, E3'],
  ['Fallback · 12 Oct', 'ok', 'BLOBs in memory passed: 81 ms', 'Load each vector table into memory once, then compare by dot product. 81 ms at 20k, under our own 200 ms target. Reading the vectors from disk on every search took 1.4 s, so that option was rejected.', 'E1, E2'],
  ['Decision · 12 Oct', null, 'BLOBs + raw SQL, same on laptop and phone', 'One table design in `schema.py`, copied into the phone app. No ORM, so the same SQL runs on both sides.', 'E9'],
  ['Re-check · 3 Nov', 'ok', 'Same result on a second, high-end phone', 'Pixel 9 Pro XL (Android 17) fails the same way as the A32. Times repeat: A32 83.5 ms vs 81 ms the first time.', 'E4'],
  ['Full test · 4 Nov · EYKO-100', 'ok', 'Android blocks every plugin, not just sqlite-vec', 'Even a made-up plugin name gives "no such function: load_extension". Real vectors from our own clips are as fast as random ones. 5 runs × 20 queries, two phones.', 'E5, E6'],
  ['Improvement · EYKO-100 → 102', 'ok', 'Our own loop was the slow part', 'In the test, a smarter loop (four running sums, keep only the best 20) gave the same top 20 on 400 of 400 checks, **5.9× faster** at 100k (537 → 91 ms). The app took the four running sums plus a faster ranking (it needs every frame\'s score to grow its time windows, so it cannot keep only 20): whole search **4.3× faster** on the A32 at 20k, 2,400 of 2,400 hits identical (Head 7).', 'E6, E7'],
  ['Limit found · 4 Nov', 'bad', 'Memory runs out between 20k and 50k rows', 'With all three vector tables loaded, 20k rows each fit, 50k does not. Android gives the app 268 MB, on the 6 GB A32 and on the 16 GB Pixel alike.', 'E8'],
  ['Re-check · 5–7 Nov · EYKO-94, 92', 'ok', 'A third phone and a second laptop agree', 'Zara ran the same test on her Infinix X670 (another maker, another chip): the same two errors, again after a phone restart, and the same memory limit. From a fresh clone on her own laptop the laptop side reproduced too: 14 tests pass and the storage test ranks the methods the same way.', 'E4, E8'],
  ['Still open', null, 'What comes next', 'Try shipping our own SQLite (EYKO-93). Choose a plan past 20k, such as smaller vectors or one table in memory (EYKO-98). Find sources for the 200 ms target and the usage estimate (EYKO-101).', null],
];
steps.forEach((s, i) => {
  const [kind, tone, title, text, show] = s;
  const col = tone === 'bad' ? C.bad : tone === 'ok' ? C.ok : C.accent;
  const right = [
    new Paragraph({ children: [new TextRun({ text: kind.toUpperCase(), size: 15, bold: true, color: C.muted, characterSpacing: 20 })], spacing: { after: 40 }, keepNext: true }),
    new Paragraph({ children: [new TextRun({ text: title, size: 22, bold: true })], spacing: { after: 60 }, keepNext: true }),
    new Paragraph({ children: runs(text, { size: 20 }), spacing: { after: show ? 60 : 0, line: 276 } }),
  ];
  if (show) right.push(new Paragraph({ children: [new TextRun({ text: 'Show: ', bold: true, size: 17, color: col }), new TextRun({ text: show, size: 17, color: col, bold: true })], spacing: { after: 0 } }));
  body.push(new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: [800, W - 800], layout: TableLayoutType.FIXED,
    rows: [new TableRow({ cantSplit: true, children: [
      cell([new TextRun({ text: String(i + 1), bold: true, size: 30, color: col })], 800, { align: AlignmentType.CENTER, borders: { top: NB, bottom: thin(), left: NB, right: { style: BorderStyle.SINGLE, size: 12, color: col } }, pad: 120 }),
      cell(right, W - 800, { borders: { top: NB, bottom: thin(), left: NB, right: NB }, pad: 120 }),
    ] })],
  }));
});

// ======================================================================
// PART C
// ======================================================================
body.push(BREAK());
body.push(H1('Part C · Hard questions'));
body.push(P([
  new TextRun({ text: 'What a strict examiner will ask about this Head. Status: ', size: 21 }), chip('Answered'), new TextRun({ text: ' proof you can show   ', size: 19 }),
  chip('Partly'), new TextRun({ text: ' some proof, gaps named   ', size: 19 }), chip('Open'), new TextRun({ text: ' not tested yet', size: 19 }),
], { after: 160 }));

const Q = [
  // id, group, q, status, say, show, push, card
  ['A1', 'A', 'Did you actually run sqlite-vec on a phone, or just read about it?', 'Answered',
    'Yes. On three real phones, run by two people: the A32 on 12 Oct, 3 and 4 Nov and the Pixel 9 Pro XL on 3 and 4 Nov (Rafique), the Infinix X670 on 5 Nov, twice, the second time after a restart (Zara). Same two errors every time: "no such module: vec0" and "no such function: load_extension".',
    'E4, E5. The proof pack: `docs/results/2026-11-05-sqlite-vec-proof-pack.md` (every raw log and device sheet). Screen recording of the Infinix run: Drive link in the proof pack.',
    'The test is one command from the phone kit (`docs/phone-kit/run-eyko94.ps1`), so anyone can rerun it while you watch.', 'Done: EYKO-94'],
  ['A2', 'A', 'Is that a sqlite-vec problem or an Android problem?', 'Answered',
    'Android. All three phones refuse to load any plugin at all, even one with a made-up name. Only modules built into Android\'s own SQLite work.',
    'E5',
    'Of fts4, fts5 and rtree, only fts4 is built in. Our keyword index uses fts4, so it is safe.', 'EYKO-89 (official reason)'],
  ['A3', 'A', 'Android apps can ship their own SQLite. Did you try that?', 'Open',
    'Not yet. Only the built-in SQLite was tried. This is the main open point of the storage decision.',
    'Nothing yet',
    'Plan: add a bundled SQLite (androidx sqlite-bundled or requery) with an arm64 sqlite-vec build on a throwaway branch, then time it against BLOBs.', 'EYKO-89, EYKO-93'],
  ['A4', 'A', 'Did it fail only on one phone?', 'Answered',
    'No. Three phones from three makers: Samsung A32 (Helio G80, Android 13), Pixel 9 Pro XL (Tensor G4, Android 17) and Infinix X670 (MediaTek MT6781, Android 13). Same failure on all three.',
    'E4',
    'Three phones are not every Android version. But the newest SQLite (3.50.6 on the Pixel) fails exactly like the oldest (3.32.2), so it is not an old-version problem.', 'Done: EYKO-94'],
  ['A5', 'A', 'Do sqlite-vec and your BLOB search return the same results, or is one just faster?', 'Open',
    'Both are exact searches with no shortcuts, so they should return the same top 20. That has not been checked yet.',
    'Nothing yet',
    'Do not mix this up with E7: there we did prove our old and new loops give identical results (400 of 400). Planned check: recall@20 against exact numpy search.', 'EYKO-91, EYKO-93'],
  ['B1', 'B', 'One run? What is the spread?', 'Answered',
    'No: 20 queries × 5 runs after a warm-up, with real vectors. The run medians stay close: at 20k, A32 81.5–83.1 ms, Pixel 37.3–37.9 ms.',
    'E6 and Figures 2–3 (the bars show the range of the 5 runs)',
    'The phones were plugged in. Controlled runs (cool, hot, low battery, third phone) are planned.', 'EYKO-95'],
  ['B2', 'B', 'Why only up to 20,000 vectors? When does a real user reach that?', 'Partly',
    'We measured up to 100k with real vectors and 300k with random ones. 20k is where memory says stop when all three tables are loaded. A user reaches 20k in about 25 days and 50k in about 2 months, if they record one hour of video a day.',
    'E6, E8',
    'The "one hour a day" has no source yet. The rate of about 13.4 kept frames per minute comes from the Ego4D phone run (Head 8).', 'EYKO-101'],
  ['B3', 'B', 'Random vectors are not real ones. Does it hold with real data?', 'Answered',
    'For speed, yes. Real vectors from our own clips take the same time: at 20k, A32 82 ms real vs 80 ms random; Pixel 37 vs 40 ms.',
    'E6',
    'This is expected: an exact dot product does the same work whatever the numbers are. Whether search finds the right frames is a retrieval question (Heads 7 and 8), not a storage one.', '—'],
  ['B4', 'B', '112 MB of memory for one table. What about all three tables, on a 4 GB phone?', 'Partly',
    'We measured all three loaded together. 20k rows each fits (app grows 53 → 160 MB on the A32). At 50k it runs out of memory on both phones. The limit is the 268 MB Android gives the app, the same on a 6 GB and a 16 GB phone.',
    'E8 and Figures 4–5',
    'A 4 GB phone has not been measured. The Infinix (8 GB) shows the same limit (E8). On the Infinix, a memory-mapped file keeps the Java memory near zero and fits all three tables at 300k rows, but it holds 1.5 GB of ordinary RAM when full and keeps a second copy of the vectors on storage (563 MB at 100k, 1.7 GB at 300k); the A32 has not been tried (EYKO-109, E8).', 'EYKO-95, EYKO-98, EYKO-109'],
  ['B5', 'B', 'The phone is about 50× slower than the laptop. Is that the chip or your code?', 'Partly',
    'Mostly our code. In the test, a smarter loop gave the same top 20 on all 400 checks and was 5.9× faster on the A32 at 100k (537 → 91 ms). Its faster scoring is now in the app, with a faster ranking: the whole search got 4.3× faster on the A32 at 20k (1.3 s → 302 ms), identical hits.',
    'E6, E7, Figure 3 · Head 7',
    'The laptop has not been rerun with the new loop, so the remaining phone-vs-laptop gap is not measured yet.', 'EYKO-91'],
  ['B6', 'B', 'Does a hot phone or a low battery slow it down?', 'Open',
    'Not measured yet. The 3 Nov Pixel run was charging at 36 °C, so it is not a clean baseline.',
    'E4 (conditions row)',
    'Planned: cool, hot (after 10 minutes of load) and low-battery runs under a fixed protocol.', 'EYKO-95, EYKO-90'],
  ['B7', 'B', 'Brute force will not scale. What is the plan past the limit?', 'Partly',
    'Speed is fine up to 100k with the new loop (91 ms on the A32). Memory is the wall, between 20k and 50k rows. We tried four ways to hold the vectors on the Infinix (EYKO-109, 7 Nov): none passes every mark. The nearest, a memory-mapped float32 file, gives identical answers and near-zero Java memory, at 14–15 % slower search; the plan is the lead\'s decision.',
    'E6, E8',
    'Tried on one phone: float32 in direct buffers (no help: Android counts it in the same 268 MB), float16 (fits only 50k, 8× slower), int8 with exact re-check (fits 100k, 386 ms, 97.4 % same hits), memory-mapped file (fits 300k, exact). Not tried: A32, keeping only the image table, an approximate index (usearch, hnswlib), bundled sqlite-vec. The whole app search is still 302 ms on the A32 at 20k.', 'EYKO-98, EYKO-109'],
  ['B8', 'B', 'Why was reading from disk twice as slow on the Pixel as on the cheaper A32?', 'Open',
    'Not explained yet. Reading 20k vectors from SQLite on every search took 3.1–3.5 s on the Pixel vs about 1.6 s on the A32. It does not affect the app, which searches from memory.',
    'E4',
    'The Pixel was charging, its storage was almost full and it reached 38 °C. We will repeat after freeing storage and under the protocol.', 'EYKO-83, EYKO-95'],
  ['C1', 'C', 'Prove the phone and the laptop store the same thing.', 'Partly',
    'There is one table design, copied into the phone. On 4 Ego4D clips the phone and laptop kept the same frames (354 of 372 at the same second), with 99 % the same place and 96 % the same action.',
    '`docs/results/2026-10-20-ego4d-baseline.md` (On the phone)',
    'There is no automatic test that the two table designs are identical. That test is planned.', 'EYKO-98'],
  ['C2', 'C', 'What does an hour of video cost in storage?', 'Partly',
    'One measured point: the database grew about 7 MB for 27.8 minutes of video, with every vector. Frame pictures were 8.8 MB per minute before dropped frames were deleted.',
    '`docs/results/2026-10-20-ego4d-baseline.md`',
    'One point is not a trend. At least 4 points on the Infinix are planned.', 'EYKO-96'],
  ['C3', 'C', 'What happens if the app is killed in the middle of writing?', 'Partly',
    'The job saves which stage it reached and resumes there. A link check fails the job if anything is missing. Tests cover this on laptop and phone.',
    '`android/app/src/test`, `src/androidTest` (queue and link tests)',
    'Nobody has yet killed the app mid-stage on a real phone. Planned: 9 force-stops at 3 stages.', 'EYKO-96'],
  ['C4', 'C', 'Why no ORM (Room entities)?', 'Partly',
    'So the same SQL runs on the laptop (sqlite3) and the phone (SupportSQLiteDatabase), and the two cannot drift apart.',
    'E1 (Room entities row)',
    'It is written down but not as a formal ADR, and there is no timing yet.', 'EYKO-98'],
  ['C5', 'C', 'You say the tests pass. How many, and what do they cover?', 'Partly',
    '109 laptop-side JVM tests and 104 on-device tests at the 2 Nov gap review.',
    '`docs/plans/gap-review-2026-11/00-gap-register.md`',
    'No coverage figure and no CI run log yet.', 'no card yet'],
  ['D1', 'D', 'MobileCLIP is research-only and YOLOE is AGPL. Can this ever ship?', 'Open',
    'They are allowed while this is an academic project. We will re-decide before any release.',
    '`docs/invariants/tooling.md` (rule)',
    'A licence list with a swap-out plan per model has not been written yet.', 'EYKO-88'],
  ['D2', 'D', 'Can someone other than you reproduce the setup?', 'Partly',
    'Yes, on the phone and on the laptop. Zara installed and ran the phone kit on her Infinix from its README alone. From a fresh clone on her own laptop: `uv sync` worked, **14 tests pass**, and the storage test ranks the methods the same way as ours. Clone to green tests: 12 min 49 s.',
    '`docs/results/2026-11-06-clean-clone-reproduction.md` (raw output pasted); her kit confirmation on EYKO-99',
    'One check fails on a fresh clone: `task smoke` looks for a memory that only exists in our own untracked `data/memories.db`. Six README fixes are listed for the lead. The Android build has not been reproduced on another laptop.', 'Done: EYKO-92 · README fixes: lead card'],
];

body.push(LABEL('All questions at a glance', { before: 0 }));
body.push(grid([700, W - 700 - 1300 - 2000, 1300, 2000], ['#', 'Question', 'Status', 'Closes with'],
  Q.map((q) => [q[0], q[2], [chip(q[3])], q[7]])));
body.push(P('Groups: A = does sqlite-vec really fail · B = speed, size and limits · C = data and design · D = licences and reproducibility.', { run: { size: 17, color: C.muted }, before: 80 }));

const GROUPS = { A: 'A · Does sqlite-vec really fail?', B: 'B · Speed, size and limits', C: 'C · Data and design', D: 'D · Licences and reproducibility' };
let curG = null;
Q.forEach((q) => {
  const [id, g, question, status, say, show, push, card] = q;
  if (g !== curG) { curG = g; body.push(H2(GROUPS[g])); }
  const lw = 1700, rw = W - lw;
  const sideB = { top: NB, left: NB, right: NB, bottom: thin() };
  body.push(new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: [lw, rw], layout: TableLayoutType.FIXED,
    rows: [
      new TableRow({ cantSplit: true, children: [cell([
        new TextRun({ text: id + '   ', bold: true, size: 20, color: C.accent }), new TextRun({ text: question + '   ', bold: true, size: 20 }), chip(status),
      ], W, { span: 2, keep: true, fill: C.head, borders: { top: thin(C.ink), left: NB, right: NB, bottom: thin() }, pad: 100 })] }),
      new TableRow({ cantSplit: true, children: [cell('**Say this**', lw, { borders: sideB, keep: true }), cell(say, rw, { borders: sideB, size: 20, keep: true })] }),
      new TableRow({ cantSplit: true, children: [cell('**Show**', lw, { borders: sideB, keep: true }), cell(show, rw, { borders: sideB, keep: true })] }),
      new TableRow({ cantSplit: true, children: [cell('**If they push**', lw, { borders: sideB, keep: true }), cell(push, rw, { borders: sideB, keep: true })] }),
      new TableRow({ cantSplit: true, children: [cell('**Closes with**', lw, { borders: sideB, color: C.muted }), cell(card, rw, { borders: sideB, color: C.muted })] }),
    ],
  }));
  body.push(P('', { after: 120 }));
});

// ======================================================================
// PART D
// ======================================================================
body.push(BREAK());
body.push(H1('Part D · Evidence'));
body.push(P('Open this part when the professor asks "show me". Each item says in one line what it proves, then the table or graph, then the file it came from. Times are per search, in milliseconds.', { run: { color: C.muted } }));

function ev(id, title, shows) {
  body.push(H2(`${id} · ${title}`));
  body.push(P([new TextRun({ text: 'What it shows: ', bold: true, size: 20 }), ...runs(shows, { size: 20 })], { after: 100, keepNext: true }));
}

ev('E1', 'Options we considered', 'Why BLOBs in memory won against the other four options.');
body.push(grid([2000, 2700, 3338, 1600], ['Option', 'What it is', 'Result', 'Verdict'], [
  ['sqlite-vec', 'SQLite plugin with a vector table (vec0)', 'Laptop 31 ms at 20k. Phone: "no such module: vec0"; "no such function: load_extension"', 'Rejected'],
  ['sqlite-vec via bundled SQLite', 'Ship our own SQLite with a native sqlite-vec per chip type', 'Not attempted: needs a Room upgrade and a native build; no official Android package found', 'Not tried'],
  ['BLOBs read every search', 'Read every vector from SQLite on each search', 'Phone 1.38 s at 20k (laptop 92 ms)', 'Rejected'],
  ['**BLOBs in memory**', 'Load each vector table once, dot product in Kotlin / numpy', 'Phone **81 ms** at 20k (laptop 1.5 ms)', '**Adopted**'],
  ['Room entities / ORM', 'Map tables to Kotlin classes', 'Would drift from the laptop\'s sqlite3 code', 'Rejected'],
], { highlight: (r) => r[3] === '**Adopted**' }));
body.push(SRC('docs/results/2026-10-12-eyko-31-vector-storage.md'));

ev('E2', 'First test: search speed by method (12 Oct)', 'On the phone, keeping the vectors in memory was about 17× faster than reading them from SQLite on every search (81 ms vs 1.38 s at 20k). Median / worst, random vectors, Samsung A32.');
body.push(grid([3238, 1600, 1600, 1600, 1600], ['Method', 'Laptop 5k', 'Laptop 20k', 'Phone 5k', 'Phone 20k'], [
  ['BLOB, read from SQLite every search', '24.1 / 33.6', '91.8 / 103.3', '245.8 / 525.0', '1379.3 / 1460.0'],
  ['**BLOB, already in memory**', '0.23 / 0.48', '1.49 / 1.74', '15.6 / 49.6', '**81.0 / 127.0**'],
  ['sqlite-vec', '8.4 / 9.6', '31.0 / 35.0', 'does not load', 'does not load'],
], { highlight: (r) => r[0].includes('memory') }));
body.push(SRC('docs/results/2026-10-12-eyko-31-vector-storage.md'));
figure('head2-vector-memory-vs-disk.png', '**Figure 1.** The same comparison repeated on 4 Nov with real vectors on both phones (log scale). Reading from SQLite on every search was timed at 1k and 5k only, because above that one search takes seconds. Source: `docs/results/vectors/*-2026-11-04-sweep-real.csv`.');

ev('E3', 'First test: file size, insert time, memory (12 Oct)', 'BLOB files are about twice the size of sqlite-vec files, and one 20k table uses 112 MB of Java memory.');
body.push(grid([4038, 2800, 2800], ['Measurement', '5,000 vectors', '20,000 vectors'], [
  ['Database file, BLOB', '20.5 MB (laptop), 20.6 MB (phone)', '82.1 MB, 82.2 MB'],
  ['Database file, sqlite-vec (laptop)', '10.6 MB', '42.5 MB'],
  ['Phone: insert all rows', '1,326 ms', '3,711 ms'],
  ['Phone: Java memory after the run', '45 MB', '112 MB'],
  ['Phone: native memory', '10 MB', '10 MB'],
]));
body.push(SRC('docs/results/2026-10-12-eyko-31-vector-storage.md'));

ev('E4', 'Re-run on three phones (3 and 5 Nov)', 'The failure repeats on a high-end phone with a newer Android and on a third phone from another maker. The Infinix is faster than the A32 at vector search, so the A32 stays our slowest phone.');
body.push(grid([2638, 2200, 2200, 2600], ['', 'Samsung A32 (3 Nov)', 'Pixel 9 Pro XL (3 Nov)', 'Infinix X670 (5 Nov, uncontrolled)'], [
  ['Android / built-in SQLite', '13 / 3.32.2', '17 / 3.50.6', '13 / 3.32.2'],
  ['sqlite-vec (vec0)', 'no such module', 'no such module', 'no such module'],
  ['load_extension', 'no such function', 'no such function', 'no such function'],
  ['20k, BLOB in memory (median / worst)', '83.5 / 114.8 (12 Oct: 81.0 / 127.0)', '40.5 / 148.4', '54.6 / 62.8 (5 runs)'],
  ['20k, BLOB read from SQLite (median)', '1,521', '3,068 (unexplained, see B8)', '1,146'],
  ['5k, BLOB in memory (median)', '16.4', '8.9', '12.2'],
  ['Conditions', '28 % battery, USB, 27.8 °C, fresh install', '57 %, charging, 36 °C, storage 97 % full', 'USB, apps open, not in flight mode; random vectors'],
], { firstColBold: true }));
body.push(SRC('docs/results/vectors/proof/ (logcat + device sheets) · docs/results/2026-11-05-sqlite-vec-proof-pack.md · docs/results/vectors/eyko90-Infinix_X670-20261105-1417.csv'));

ev('E5', 'Plugin check: is it Android or sqlite-vec? (4 and 5 Nov)', 'Android refuses every loadable plugin, even a made-up name, on all three phones. So it is not a sqlite-vec bug.');
body.push(grid([2638, 2333, 2333, 2334], ['Check', 'A32 (Android 13, SQLite 3.32.2)', 'Pixel (Android 17, SQLite 3.50.6)', 'Infinix X670 (Android 13, SQLite 3.32.2)'], [
  ['sqlite-vec: CREATE … USING vec0', 'no such module: vec0', 'no such module: vec0', 'no such module: vec0'],
  ["load_extension('vec0')", 'no such function: load_extension', 'no such function: load_extension', 'no such function: load_extension'],
  ['load_extension of a made-up name', '**no such function: load_extension**', '**no such function: load_extension**', '**no such function: load_extension**'],
  ['fts4 / fts5 / rtree (built in or not)', 'fts4 works; fts5 and rtree: no such module', 'fts4 works; fts5 and rtree: no such module', 'fts4 works; fts5 and rtree: no such module'],
  ['PRAGMA compile_options', 'none listed', 'none listed', 'none listed'],
]));
body.push(SRC('docs/results/vectors/proof/*-2026-11-04-extensions-logcat.txt · infinix-2026-11-05-logcat.txt'));

ev('E6', 'Speed with real vectors: old loop vs faster loop (4 Nov)', 'Real vectors, 5 runs × 20 queries. The faster loop returned the same top 20 on all 400 checks at every size, on both phones.');
body.push(grid([1638, 2000, 2000, 2000, 2000], ['Vectors', 'A32: old loop', 'A32: faster loop', 'Pixel: old loop', 'Pixel: faster loop'], [
  ['1k', '3.1 ms', '**1.2 ms** (2.7×)', '1.6 ms', '**0.6 ms** (2.8×)'],
  ['5k', '16 ms', '**4.9 ms** (3.3×)', '8.6 ms', '**2.5 ms** (3.4×)'],
  ['20k', '82 ms', '**19 ms** (4.4×)', '37 ms', '**7.9 ms** (4.7×)'],
  ['50k', '246 ms', '**46 ms** (5.4×)', '102 ms', '**20 ms** (5.2×)'],
  ['100k', '537 ms', '**91 ms** (5.9×)', '262 ms', '**39 ms** (6.7×)'],
], { firstColBold: true, highlight: (r) => r[0] === '20k' }));
figure('head2-vector-memory-speed.png', '**Figure 2.** Search time by table size with the old loop, both phones on one chart, real vectors. The bar on each point is the range of the 5 runs.');
figure('head2-vector-fast-loop.png', '**Figure 3.** Old loop vs faster loop with real vectors; same answers. The bar on each point is the range of the 5 runs. The faster scoring is in the app since EYKO-102.');
body.push(SRC('docs/results/vectors/*-2026-11-04-sweep-real.csv'));
body.push(P('**Vector part vs whole search.** These times are the vector loop alone. The search the app runs also reads every frame row and ranks frames into time windows. End to end on the A32 at 20k it took 1.3 s before EYKO-102 and **302 ms after** (Pixel 119 ms), with identical hits. Full detail is in Head 7.', { run: { size: 20 } }));

ev('E7', 'The two loops, in plain words', 'Why the faster loop gives exactly the same answer: both score every row exactly; only the method differs.');
body.push(P('Every search does two jobs. **1. Score every stored vector:** multiply the query\'s numbers with the stored vector\'s numbers pair by pair and add them up (the dot product; higher means more alike). **2. Keep the best 20.**', { run: { size: 20 } }));
body.push(grid([2038, 3800, 3800], ['', 'Old loop (app until EYKO-102)', 'Faster loop (EYKO-100 test)'], [
  ['Job 1: scoring', 'One running total per row. Each multiply-add waits for the one before it.', 'Four running totals per row, added at the end. The CPU works on all four at the same time.'],
  ['Job 2: best 20', 'Store all scores, then **sort every row** and keep the first 20.', 'Keep a **20-slot "best so far" list**. A new score goes in only if it beats the worst of the 20.'],
  ['Work at 100k', 'About 1.7 million comparisons, plus 100,000 throwaway objects per search.', 'About 100,000 comparisons. No objects.'],
  ['Extra memory', '100,000 scores + 100,000 objects', '20 scores + 20 row numbers'],
  ['Answer', 'The 20 best rows', 'The same 20 rows: 400 of 400 checks, every size, both phones'],
  ['Where in code', '`VideoVectors.kt` → `knn()` (before EYKO-102)', '`VectorStorageSpikeTest.kt` → `topKFast()` (test only)'],
], { firstColBold: true }));
body.push(P('**What the app runs since EYKO-102:** the four running sums (`VideoVectors.scores()`), but not the 20-slot list. The app\'s search needs every frame\'s score to grow its time windows, so it ranks all frames with one fast sort of packed numbers (`rankDescending()`). Same hits as before, checked on 2,400 of 2,400. Details: Head 7.', { run: { size: 20 }, before: 100 }));
body.push(P('Not measured separately: how much of the gain comes from the four totals and how much from not sorting. The faster loop does not fix memory; the vectors still have to be loaded.', { run: { size: 18, color: C.muted }, before: 100 }));

ev('E8', 'Memory with all three vector tables loaded (4 Nov)', 'Memory is the real limit: 20k rows per table fit, 50k does not, on both phones.');
body.push(grid([1638, 1600, 3200, 3200], ['Rows per table', 'Vectors need', 'A32: app memory before → after', 'Pixel: app memory before → after'], [
  ['5k', '28 MB', '53 → 80 MB; all 3 tables loaded', '57 → 84 MB; all 3 tables loaded'],
  ['20k', '113 MB', '53 → 160 MB; all 3 tables loaded', '57 → 164 MB; all 3 tables loaded'],
  ['50k', '282 MB', '53 → 224 MB; **out of memory**, 2 of 3 loaded', '57 → 228 MB; **out of memory**, 2 of 3 loaded'],
  ['100k', '563 MB', '53 → 248 MB; **out of memory**, 1 of 3 loaded', '57 → 252 MB; **out of memory**, 1 of 3 loaded'],
], { firstColBold: true, highlight: (r) => r[0] === '20k' }));
figure('head2-vector-heap.png', '**Figure 4.** One table on its own: what its vectors need against the 268 MB Android gives the app. Real vectors ran on both phones up to 100k (205 MB). The line goes on to 300k as arithmetic (614 MB); 300k was run only with random vectors on 3 Nov, where both phones ran out of memory.');
figure('head2-vector-all-tables.png', '**Figure 5.** All three vector tables in memory. At 50k the third table, at 100k the second table no longer fits in the 268 MB Java memory Android gives the app.');
body.push(SRC('docs/results/vectors/*-2026-11-04-memory.csv'));
body.push(P('**A third phone shows the same limit (Infinix X670, 5 Nov, uncontrolled run):** 20k rows each fit (app memory 86 → 167 MB); at 50k only 2 of 3 tables load and at 100k only 1, with the same "Failed to allocate" errors and the same 268 MB limit. Not drawn in Figure 5 because it was not a protocol run. Raw data: `docs/results/vectors/eyko100-memory-Infinix_X670-20261105-1414.csv`.', { run: { size: 20 } }));
body.push(P('**Four ways to hold the vectors (EYKO-109, Infinix X670 only, 7 Nov).** Java memory after loading all three tables / tables loaded: today\'s array at 20k 116 MB, 3 of 3; at 50k 183 MB, **2 of 3**; at 100k 208 MB, **1 of 3**. Float32 in direct buffers: identical to today (Android counts direct buffers in the same 268 MB). Float16: 50k fits (145 MB), 100k 2 of 3. Int8 with exact re-check: 100k fits (146 MB), 200k 2 of 3. Memory-mapped float32 file: 300k fits with 10 MB of Java memory, but 1,484 MB of total memory when full. Speed at 100k (scores for all rows): today 297 ms, direct 340, mapped 341, int8 386, float16 2,341. Answers against today (whole app search, 800 hits): mapped 800 of 800 identical, int8 779, float16 737 (799 as a set). After 5 minutes in the background with other apps open the mapped vectors were not killed, but the first search was 3.8× slower. None passes every mark on the card. Full tables: `docs/results/2026-11-07-vectors-off-heap.md`; A32 and Pixel not run.', { run: { size: 20 }, before: 100 }));
body.push(SRC('docs/results/vectors/offheap/*.csv'));
body.push(P('**Extra proof from the random-vector sweep (EYKO-90, 3 Nov):** one table of 300k vectors needs a single 614 MB block. Both phones refused: "Failed to allocate a 614400016 byte allocation … growth limit 268435456". Raw data: `docs/results/vectors/*-2026-11-03-sweep.csv`.', { run: { size: 20 } }));

ev('E9', 'What the database holds', 'One table design, written once in `src/video_memory/schema.py` and copied into the phone\'s `VideoSchema.kt`. Every kept frame is tied to its video and second, so a search hit can show the exact moment.');
body.push(grid([2338, 4700, 2600], ['Table', 'What one row holds', 'Written by'], [
  ['videos', 'One recorded clip: id, file path, time, duration, GPS, status (processing / ready / failed)', 'Intake (EYKO-2)'],
  ['jobs', 'The background job for a video: stage reached, attempts, status, last error', 'Queue (EYKO-3)'],
  ['frames', 'Every pulled frame: second in video, file path, kept or dropped and why, dHash', 'split, filter, dedup'],
  ['scene_records', 'One per kept frame: objects, people count, place, action, caption', 'scene, small_objects'],
  ['video_texts', 'Captions (transcripts later) with a keyword index', 'embed_texts'],
  ['image_vec', '512-number MobileCLIP vector per kept frame (float32 BLOB)', 'embed_images'],
  ['text_vec', '384-number bge-small vector per text (float32 BLOB)', 'embed_texts'],
  ['object_sightings', 'Each detected object with its crop vector and whether it is the latest sighting', 'latest'],
  ['transcript_chunks, audio_windows, audio_vec', 'Speech and sound. Tables exist; nothing writes them yet.', 'Speech head (later)'],
], { firstColBold: true }));
body.push(SRC('src/video_memory/schema.py · android/…/video/VideoSchema.kt'));

body.push(H2('Limits: how these numbers could mislead'));
[
  'All runs were on phones plugged in by cable, so this is not a controlled protocol yet (EYKO-95).',
  'The Pixel was charging and warm (36–38 °C) during the 3 Nov runs.',
  'A 4 GB phone has not been measured. The Infinix numbers so far come from an uncontrolled run (plugged in, apps open); its protocol runs are EYKO-95.',
  'Real search also filters by video status, which adds a join that the storage test does not include.',
  'BLOB files are about twice the size of sqlite-vec files (E3).',
].forEach((t) => body.push(bullet(t)));

// ======================================================================
// PART E
// ======================================================================
body.push(BREAK());
body.push(H1('Part E · Words, gaps, upkeep'));
body.push(H2('Words in plain language'));
body.push(grid([2338, W - 2338], ['Word', 'What it means here'], [
  ['Vector', 'A list of numbers that describes a frame or a caption. Similar things get similar numbers. Ours: 512 numbers per frame, 384 per caption.'],
  ['BLOB', 'A database column that just holds raw bytes. We pack each vector\'s numbers into one.'],
  ['float32', 'A number stored in 4 bytes. 512 of them = 2 KB per frame vector.'],
  ['sqlite-vec', 'A plugin that adds vector search to SQLite. Works on the laptop, blocked on Android.'],
  ['load_extension', 'The SQLite function that loads plugins. Android\'s SQLite does not have it.'],
  ['Dot product', 'Multiply two vectors number by number and add it all up. Higher means more alike.'],
  ['Brute force / exact search', 'Compare the query with every stored vector. Always finds the true best matches, but cost grows with the number of rows.'],
  ['Approximate index', 'A shortcut structure (e.g. usearch, hnswlib) that skips most rows. Much faster at scale, may miss a few matches.'],
  ['Java heap', 'The memory Android lets the app use for its objects. 268 MB on both our phones.'],
  ['PSS', 'The app\'s total memory as Android counts it.'],
  ['ORM', 'A library that maps tables to code classes (Room on Android). We use plain SQL instead.'],
  ['Spike', 'A short, throwaway test to answer one question before building on it.'],
  ['recall@20', 'Of the true top 20 matches, how many a method returns. 20 of 20 = 100 %.'],
  ['Parity', 'Laptop and phone give the same result for the same input.'],
], { firstColBold: true }));

body.push(H2('Open gaps for this Head'));
body.push(grid([800, 3938, 1600, 1100, 2200], ['Gap', 'What is missing', 'Card', 'Severity', 'Resolution'], [
  ['G20', 'Vectors in memory hit the 268 MB limit between 20k and 50k rows per table (one table alone: about 100k). No plan for larger libraries.', 'EYKO-98, 100, 101, 109', 'High', 'Partly (EYKO-109, 7 Nov, Infinix only): four storage ways tried, none passes every mark; a memory-mapped file fits 300k rows exactly but 14–15 % slower and 1.5 GB of RAM. A32 and Pixel not run; the lead decides.'],
  ['G21', 'The app used the slow search loop.', 'lead', 'Medium', 'Done 4 Nov (EYKO-102): 4.3× (A32) / 4.1× (Pixel) faster at 20k, 2,400 of 2,400 hits identical.'],
  ['G9', 'Phone retrieval rule (BM25 + dense + RRF) and video search (dense only) disagree. Needs an ADR.', 'EYKO-81', 'Medium', ''],
  ['G13', 'The A32 only ran this test, never the video pipeline.', 'EYKO-84', 'Medium', 'Done 5 Nov (EYKO-84): a second phone, Zara\'s Infinix X670, ran the whole pipeline on both kit clips to "ready", no crash, peak memory 1.10 GiB (`docs/results/2026-11-05-second-phone-first-run.md`). Still open: the same two clips on the Pixel for a same-clip comparison.'],
  ['G17', 'Two broken tools: frame_report pull needs Python 3.12; task test-android / build-android call bare gradlew.bat.', 'EYKO-70', 'Low', ''],
  ['G19', 'Licences to re-decide before release: MobileCLIP research-only, YOLOE AGPL.', 'EYKO-88', 'Low', ''],
  ['G12', 'Speech tables exist but nothing writes them.', 'EYKO-86', 'Low', ''],
]));

body.push(H2('How to update this document'));
[
  'When a card closes: change the question\'s status in Part C, rewrite "Say this" with the new numbers, add the new table or graph to Part D as the next E number, and change the date on the cover.',
  'If the result changes a number in Part A, update Part A too. Part A must always match the latest evidence.',
  'Never delete an old finding. If a new run disagrees, say so in "Say this" and keep the old table in Part D.',
  'Add a step to Part B only for something that changed the direction of the work.',
].forEach((t) => body.push(bullet(t)));

body.push(H2('References'));
[
  'Storage test write-up: `docs/results/2026-10-12-eyko-31-vector-storage.md`',
  'Table design: `src/video_memory/schema.py`; phone: `android/…/video/VideoSchema.kt`, `VideoVectors.kt`',
  'Rules: `docs/invariants/core.md` (parity), `security.md` (DB), `tooling.md` (uv, licences)',
  'Gap review: `docs/plans/gap-review-2026-11/00-gap-register.md`',
].forEach((t) => body.push(bullet(t)));

// ======================================================================
const doc = new Document({
  creator: 'Eykon', title: 'Head 2 · Setup & storage',
  styles: {
    default: { document: { run: { font: FONT, size: 21, color: C.ink } } },
    paragraphStyles: [
      { id: 'Title', name: 'Title', basedOn: 'Normal', run: { font: FONT, size: 52, bold: true, color: C.ink }, paragraph: { spacing: { before: 0, after: 80 }, keepNext: true } },
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 34, bold: true, color: C.accent }, paragraph: { spacing: { before: 0, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 25, bold: true, color: C.ink }, paragraph: { spacing: { before: 320, after: 100 }, keepNext: true, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: FONT, size: 22, bold: true, color: C.ink }, paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [{ reference: 'bul', levels: [
    { level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 260 } } } },
    { level: 1, format: LevelFormat.BULLET, text: '–', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 260 } } } },
  ] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [
      new TextRun({ text: 'Eykon · Head 2 · Setup & storage  ·  page ', size: 16, color: C.muted }),
      new TextRun({ children: [PageNumber.CURRENT], size: 16, color: C.muted }),
    ] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = process.argv[2] || path.join(__dirname, '..', 'Head-2-Setup-and-storage.docx');
  fs.writeFileSync(out, buf);
  console.log('wrote', out, buf.length);
});
