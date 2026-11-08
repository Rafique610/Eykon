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
  ['**Overall status**', 'Built and in the app. Re-tested on two phones with real vectors; the failure confirmed on a third phone, and the setup reproduced on a second laptop. Memory limit found; plan for it still open. Why Android blocks plugins is now traced to its source, and the routes around it are researched (not yet tried on a phone).'],
  ['**Cards**', 'EYKO-1 (tables), EYKO-31 (storage test), EYKO-30 (pytest), EYKO-90 (size sweep), EYKO-100 (full test), EYKO-102 (faster search in app), EYKO-94 (three-phone proof pack), EYKO-92 (clean clone), EYKO-84 (second phone, whole pipeline), EYKO-89 (why Android blocks plugins, routes around it)'],
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
  ['Open', 'Our own sqlite-vec file for Android is built and checked (EYKO-104), but not yet run through a bundled SQLite on a phone, the only way left to run sqlite-vec on Android (EYKO-105–107).'],
  ['Open', 'No chosen plan yet for libraries past 20k–50k frames (EYKO-98).'],
  ['Partly', 'The 200 ms pass mark and the "1 hour of video a day" estimate have no source yet (EYKO-101).'],
  ['Partly', 'On battery the A32 searches 1.2–1.4× slower than on the cable, and our earlier A32 speeds were all on the cable (8 Nov, EYKO-112). Heat and low battery were not measurable on the Infinix; A32 hot / low battery and the Pixel are still to run.'],
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
  ['Research · 5 Nov · EYKO-89', 'ok', 'The reason is one line in Android\'s source', 'Android builds its SQLite with `-DSQLITE_OMIT_LOAD_EXTENSION`, unchanged from Android 11 to today. Three ready-made SQLite builds that do load plugins were found and compared (Google\'s bundled SQLite, requery, SQLCipher). Google\'s is the one to try on the phone. Two new problems found: the ready-made sqlite-vec file is built for 4 KB memory pages and has no NEON speed-up on Android.', 'E10, E11'],
  ['Re-check · 5–7 Nov · EYKO-94, 92', 'ok', 'A third phone and a second laptop agree', 'Zara ran the same test on her Infinix X670 (another maker, another chip): the same two errors, again after a phone restart, and the same memory limit. From a fresh clone on her own laptop the laptop side reproduced too: 14 tests pass and the storage test ranks the methods the same way.', 'E4, E8'],
  ['Build · 7 Nov · EYKO-104', 'ok', 'Our own sqlite-vec file for Android', 'The ready-made Android file of sqlite-vec is aligned for 4 KB pages and has no NEON speed-up (EYKO-89). So we built v0.1.9 ourselves with NDK r28c, once with NEON and once without. Both are aligned for 16 KB pages, export `sqlite3_vec_init` and need only libc, libm and libdl. Rebuilding gives the same SHA256. Not yet loaded on a phone.', 'E1'],
  ['Test · 8 Nov · EYKO-105', 'ok', 'Our own SQLite works on the phone, but it is slower', 'On the A32, Google\'s bundled SQLite loaded our own sqlite-vec file. It gave the same top 20 as our search at every size (400 of 400), and three tables at 100k rows stayed at about 56 MB, where our way runs out of memory at 50k. But it was **2.5× slower** (230 against 91 ms at 100k), and it can return at most 4,096 rows, while the app needs every frame\'s score. Zara\'s own SQLite build (R4) ran at the same speed on the same phone (231 ms). Verdict: works, not adopted.', 'E11'],
  ['Test · 8 Nov · EYKO-106', 'bad', 'requery is cheaper to adopt, but no faster', 'The lead asked to try requery too, because it works with our Room as it is. It loaded the same sqlite-vec file on the A32 and gave the same top 20, but first took **486 ms at 100k**, 2.1× Google\'s SQLite. We tested why: requery makes every new database with **1 KB pages** (its default is hard-coded to 1024), and Google uses 4 KB. On the same file both engines run at the same speed (234 against 236 ms). With 4 KB pages requery matches R1, still 2.5× our in-memory search. Verdict: works, not adopted.', 'E11'],
  ['Still open', null, 'What comes next', 'Choose between the memory fixes: a memory-mapped file (EYKO-109) or sqlite-vec (EYKO-105, 108) (EYKO-98). Find sources for the 200 ms target and the usage estimate (EYKO-101).', null],
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
    'Android. Its own SQLite is built with plugin loading switched off: the line `-DSQLITE_OMIT_LOAD_EXTENSION` in Android\'s source (`external/sqlite/dist/Android.bp`), present from Android 11 to the current version. All three phones also refuse a plugin with a made-up name, so it is not sqlite-vec.',
    'E10, E5',
    'The same file explains the rest of the phone log: fts4 is switched on, fts5 and rtree are not, and the compile-options list is empty because that list is switched off too. Android\'s own Java layer never loads plugins either.', 'Done: EYKO-89'],
  ['A3', 'A', 'Android apps can ship their own SQLite. Did you try that?', 'Answered',
    'Yes, on the A32. Google\'s bundled SQLite (`BundledSQLiteDriver.addExtension`) loaded our own sqlite-vec file: same top 20 as our search at every size, and three tables at 100k fit in about 56 MB. But it is 2.5× slower than our in-memory search (230 against 91 ms at 100k) and returns at most 4,096 rows. Zara\'s own SQLite build (R4) is just as fast on the same phone. So we did not adopt it.',
    'E11 · `docs/results/2026-11-08-route-r1-bundled.md`',
    'Before the test: we rebuilt sqlite-vec ourselves (4 KB pages and no NEON in the ready-made file). Even testing it raised the app\'s androidx.sqlite from 2.4.0 to 2.7.1, because Android\'s build tools keep test and app on one version. The Pixel and Infinix runs are not done. R2 (requery, EYKO-106) also works. It first measured 486 ms at 100k because of its 1 KB default page size; with 4 KB pages it matches R1. R3 (SQLCipher) was dropped by the owner on 8 Nov: same search, plus decryption on every read, and no card asks for encryption.', 'EYKO-104, 105, 106, 108; 107 (dropped)'],
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
    'A 4 GB phone has not been measured. The Infinix is the next test.', 'EYKO-95, EYKO-98'],
  ['B5', 'B', 'The phone is about 50× slower than the laptop. Is that the chip or your code?', 'Partly',
    'Mostly our code. In the test, a smarter loop gave the same top 20 on all 400 checks and was 5.9× faster on the A32 at 100k (537 → 91 ms). Its faster scoring is now in the app, with a faster ranking: the whole search got 4.3× faster on the A32 at 20k (1.3 s → 302 ms), identical hits.',
    'E6, E7, Figure 3 · Head 7',
    'The laptop has not been rerun with the new loop, so the remaining phone-vs-laptop gap is not measured yet.', 'EYKO-91'],
  ['B6', 'B', 'Does a hot phone or a low battery slow it down?', 'Partly',
    'Heat and low battery: not measurably on the Infinix (within 1 % of the cool run; 5 C warmer, 24 % battery). Being on battery: yes on the A32. Unplugged it searched **1.2 to 1.4× slower** than with the cable in (same build, same day; fast loop at 100k: 126 against 91 ms). Every earlier A32 speed was measured on the cable.',
    '`docs/results/2026-11-05-vectors-phone-sweep.md` (Infinix cool / hot / low battery; A32 cool run + cable-in control)',
    'Cause not tested: probably lower CPU clock speeds on battery (short searches are unaffected). Still to run: A32 hot and low battery, the Pixel, and CPU frequency logging.', 'EYKO-95, EYKO-112'],
  ['B7', 'B', 'Brute force will not scale. What is the plan past the limit?', 'Partly',
    'Speed is fine up to 100k with the new loop (91 ms on the A32). Memory is the wall, between 20k and 50k rows. The options are researched with sources; the plan is a proposal, not chosen: (1) vectors outside Java memory as int8 or float16, still exact; (2) bundled sqlite-vec, measured for memory and file size; (3) an approximate index (usearch) past about 200k.',
    'E6, E8, E11',
    'usearch is the fallback index for the laptop test: approximate, can read its index straight from disk, int8 / float16, official Android build. hnswlib has no Android build; FAISS has no Android package; ObjectBox would replace SQLite. Note the whole app search is still 302 ms on the A32 at 20k.', 'EYKO-91, EYKO-98'],
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
  ['sqlite-vec via bundled SQLite', 'Ship our own SQLite with a native sqlite-vec per chip type', '12 Oct: not attempted. 5 Nov research (E11): Google\'s bundled SQLite loads plugins (`addExtension`, androidx.sqlite 2.6.0); sqlite-vec ships Android files but they need rebuilding (4 KB pages, no NEON). 7 Nov: rebuilt and checked (EYKO-104): 16 KB pages, NEON. Not yet run on a phone (EYKO-105–107)', 'In test'],
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

ev('E10', 'Why Android blocks plugins: the line in its source (5 Nov)', 'Android\'s own SQLite is compiled with plugin loading removed, in every release from Android 11 to today. Not a sqlite-vec bug, and not fixed by a newer Android.');
body.push(grid([3238, 3200, 3200], ['Android source branch', 'Line in `dist/Android.bp`', 'Our phone on it'], [
  ['android11-release', '36: `-DSQLITE_OMIT_LOAD_EXTENSION`', '—'],
  ['android13-release', '66: same line', 'Samsung A32 (Android 13, SQLite 3.32.2)'],
  ['android14-release / 15-release', '66: same line', '—'],
  ['android16-release', '67: same line', '—'],
  ['main (current)', '67: same line', 'Pixel 9 Pro XL (Android 17, SQLite 3.50.6)'],
], { firstColBold: true }));
body.push(P('**How the phone log follows from the same file:** fts3 / fts4 are switched on, fts5 and rtree are not, and `-DSQLITE_OMIT_COMPILEOPTION_DIAGS` is why the compile-options list is empty (E5). The Java layer, `android_database_SQLiteConnection.cpp` (1,036 lines), never mentions plugins at all.', { run: { size: 20 }, before: 100 }));
body.push(SRC('docs/results/eyko-89-android-sqlite-extensions/01-why-android-blocks-extensions.md · evidence/aosp-android-bp-flags.txt'));

ev('E11', 'Ways to ship our own SQLite, and the vector options (5 Nov)', 'Three ready-made SQLite builds load plugins on Android. Google\'s is the one to try first. The ready-made sqlite-vec file needs rebuilding before it is used.');
body.push(grid([2200, 2600, 2600, 2238], ['Route', 'Plugin loading', 'Cost for our app', 'Verdict'], [
  ['**Google bundled SQLite** (androidx sqlite-bundled)', '`addExtension(file, entryPoint)` since 2.6.0; SQLite 3.53.4, FTS5 on', 'Test: app androidx.sqlite 2.4.0 → 2.7.1 (build tools keep test and app on one version). App: Room 2.6.1 → 2.8 + support wrapper', 'Tried 8 Nov (EYKO-105): works, 2.5× slower, **not adopted**'],
  ['requery sqlite-android', '`customExtensions`; FTS5 on; ~1.7 MB arm64', 'Works with Room 2.6.1 as it is (needs only androidx.sqlite 2.4.0). New databases get 1 KB pages unless set to 4 KB', 'Tried 8 Nov (EYKO-106): works, same speed as R1 with 4 KB pages, **not adopted**'],
  ['SQLCipher', 'Turned on for every connection; FTS5 on', 'Room 2 factory, but needs a password and key storage', '**Dropped** 8 Nov (EYKO-107): same search plus decryption, no card asks for encryption'],
  ['Our own NDK build', 'Not needed: sqlite-vec compiled in', 'Our own native build and JNI', 'Last resort'],
], { firstColBold: true }));
body.push(P('**Result on the phone (8 Nov, Samsung A32, EYKO-105):** median ms of 5 runs × 20 queries, top 20, same vectors and queries; recall@20 = 1.0 everywhere.', { run: { size: 20 }, before: 100 }));
body.push(grid([2200, 2600, 2600, 2238], ['Rows', 'R1: Google\'s SQLite + our sqlite-vec', 'R4: own SQLite with sqlite-vec (Zara\'s build)', 'Our in-memory search'], [
  ['20,000', '53.0', '50.8', '18.5'],
  ['100,000', '**230.2**', '**231.0**', '**91.2**'],
  ['R2 requery, its default 1 KB pages: 20,000 / 100,000', '104.5 / **485.8** (same A32)', '—', '20.4 / 93.2 (same run)'],
  ['R2 requery, 4 KB pages: 100,000', '**233.8**', '—', '—'],
  ['3 tables × 100k, app memory', '55 MB, no error', 'flat (Infinix, EYKO-108)', 'out of memory at 50k'],
], { firstColBold: true }));
body.push(SRC('docs/results/2026-11-08-route-r1-bundled.md · docs/results/vectors/routes/a32-*.csv · proof/a32-2026-11-08-route-r1-logcat.txt'));
body.push(P('**Why requery (R2) first ran 2× slower (8 Nov, A32, 100k rows, median ms):** both engines searched the same two files, one written by each. 12 runtime settings were logged (`PRAGMA page_size, cache_size, mmap_size, journal_mode, …`); only the page size differs between the files. requery makes new databases with 1 KB pages because its `SQLiteGlobal.getDefaultPageSize()` returns a hard-coded 1024 (requery 3.49.0 source); Google uses 4 KB. Matching requery\'s other settings to Google\'s changed nothing. Likely mechanism, not separately measured: sqlite-vec keeps vectors in 2 MB chunk BLOBs, which take about 2,000 pages each at 1 KB and about 500 at 4 KB. Compile flags were checked and ruled out (requery `-O3`, Google `-Oz`). Fix if R2 were used: `PRAGMA page_size = 4096` before the first table.', { run: { size: 20 }, before: 100 }));
body.push(grid([2400, 1400, 1900, 1900, 2038], ['File', 'Page size', 'Google searches it', 'requery searches it', 'requery, Google\'s settings'], [
  ['written by Google', '4,096 B', '235.8', '**233.8**', '233.0'],
  ['written by requery', '1,024 B', '**485.0**', '485.1', '482.1'],
], { firstColBold: true }));
body.push(SRC('docs/results/2026-11-08-route-r2-requery.md · proof/a32-2026-11-08-route-r2-diagnose-logcat.txt · RouteR2DiagnoseTest.kt'));
body.push(P('**Each route has its own test card**, all under one shared protocol and the same pass marks: EYKO-104 (build our own sqlite-vec file), EYKO-105 (R1 Google bundled), EYKO-106 (R2 requery), EYKO-107 (R3 SQLCipher, dropped 8 Nov), EYKO-108 (R4 own NDK build). Option O1, vectors outside Java memory: EYKO-109.', { run: { size: 20 }, before: 100 }));
body.push(grid([3238, 3200, 3200], ['Ready-made Android file (checked with `readelf`)', 'Memory-page alignment', 'Speed-up (NEON)'], [
  ['sqlite-vec v0.1.9 `vec0.so` (arm64)', '**4 KB** (`0x1000`); 16 KB needed on 16 KB phones and by Google Play from 1 Feb 2027', '**None**: the build script turns NEON on only for Mac'],
  ['usearch v2.26.6 `libusearch_c.so` (arm64)', '**4 KB** (`0x1000`)', 'not checked'],
], { firstColBold: true }));
body.push(P('**Past brute force (B7), a proposal:** (1) vectors outside Java memory, as int8 or float16, still exact; (2) bundled sqlite-vec, judged on memory and file size, since without NEON it may be slower than our loop; (3) usearch, an approximate index that reads from disk, tested on the laptop first for recall@20 ≥ 0.95 (EYKO-91).', { run: { size: 20 }, before: 100 }));
body.push(SRC('docs/results/eyko-89-android-sqlite-extensions/ (README, 02, 03, 04, sources.md, evidence/prebuilt-so-alignment.txt)'));

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
  ['G20', 'Vectors in memory hit the 268 MB limit between 20k and 50k rows per table (one table alone: about 100k). No plan for larger libraries.', 'EYKO-98, 100, 101', 'High', ''],
  ['G21', 'The app used the slow search loop.', 'lead', 'Medium', 'Done 4 Nov (EYKO-102): 4.3× (A32) / 4.1× (Pixel) faster at 20k, 2,400 of 2,400 hits identical.'],
  ['G9', 'Phone retrieval rule (BM25 + dense + RRF) and video search (dense only) disagree. Needs an ADR.', 'EYKO-81', 'Medium', ''],
  ['G13', 'The A32 only ran this test, never the video pipeline.', 'EYKO-84', 'Medium', 'Done 5 Nov (EYKO-84): a second phone, Zara\'s Infinix X670, ran the whole pipeline on both kit clips to "ready", no crash, peak memory 1.10 GiB (`docs/results/2026-11-05-second-phone-first-run.md`). Still open: the same two clips on the Pixel for a same-clip comparison.'],
  ['G17', 'Two broken tools: frame_report pull needs Python 3.12; task test-android / build-android call bare gradlew.bat.', 'EYKO-70', 'Low', ''],
  ['G19', 'Licences to re-decide before release: MobileCLIP research-only, YOLOE AGPL.', 'EYKO-88', 'Low', ''],
  ['G12', 'Speech tables exist but nothing writes them.', 'EYKO-86', 'Low', ''],
  ['G24', 'Native files built for 4 KB memory pages: the ready-made sqlite-vec and usearch files (checked). The app\'s own ONNX Runtime 1.18.0 and LiteRT-LM files are not checked. Google Play blocks such updates from 1 Feb 2027.', 'no card yet', 'Medium', 'Found 5 Nov (EYKO-89).'],
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
