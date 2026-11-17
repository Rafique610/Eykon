// Head 3 defense doc (layout and rules: docs/documents/HEAD-DOC-TEMPLATE.md; helpers copied from head2-defense.js).
// Usage: node head3-defense.js  (from this folder; writes ../Head-3-Video-intake.docx)
// Graphs come from figures/ (redraw them first: uv run docs/documents/source/figures/head3_intake.py).
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
body.push(P([new TextRun({ text: 'EYKON  ·  DEFENSE NOTES  ·  HEAD 3 OF THE PIPELINE', bold: true, size: 16, color: C.accent, characterSpacing: 30 })], { after: 80 }));
body.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun('Video intake')] }));
body.push(P('From a clip picked on the phone to a background job that runs ten stages, survives crashes and finishes with the app closed.', { run: { color: C.muted, size: 22 }, after: 200 }));

body.push(grid([2100, W - 2100], null, [
  ['**Last updated**', '17 Nov 2026'],
  ['**Overall status**', 'Built, in the app and measured on three phones (Pixel 9 Pro XL, Infinix X670, Samsung A32). Jobs now run as Android background work with a notification, so they finish with the app closed, the screen off and the phone in deep sleep. A crash or a kill resumes at the stage after the last saved one with identical output. The app reads the picked video in place (no copy, no 500 MB limit) and refuses the same file twice. Not done: faster models (EYKO-121) and the A32\'s background check (EYKO-168).'],
  ['**Cards**', 'EYKO-2 (add a clip), EYKO-3 (job queue), EYKO-16 (finish), EYKO-44 (background work), EYKO-71 (duplicates, free space), EYKO-85 (long clip in the background), EYKO-116 Part 3 (kill mid-stage), EYKO-117 (phone harness), EYKO-118 (bad inputs), EYKO-119 (safe reruns), EYKO-120 (`latest` profile), EYKO-122 (Android rules), EYKO-123 (Pixel run), EYKO-126 (read in place), EYKO-127 (recording place), EYKO-64 (Pixel timing)'],
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
    P('A person picks a video; the app reads it **in place**, refuses it if the same file is already saved, and makes **one job of ten stages**. The job runs as Android **background work with a notification**, so it finishes with the app closed and the screen off. After each stage the job saves how far it got: a crash or a kill **resumes at the next stage with the same output**. A minute of video costs the Pixel **0.85 to 1.57 minutes** of work the Infinix **1.80 to 3.22**, and the slowest phone, the A32, **2.69 to 4.53**.', { run: { size: 23 }, after: 0, line: 300 }),
  ], W, { fill: C.accentSoft, pad: 160, borders: { top: NB, bottom: NB, right: NB, left: { style: BorderStyle.SINGLE, size: 24, color: C.accent } } })] })],
}));

body.push(LABEL('Where it sits in the pipeline'));
const stages = ['Record video', 'Pick + read', 'Job queue', 'Frames: split, filter, dedup', 'Scene, vectors, latest', 'Search'];
const sw = Math.floor(W / stages.length);
const swArr = stages.map((_, i) => (i === stages.length - 1 ? W - sw * (stages.length - 1) : sw));
body.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: swArr, layout: TableLayoutType.FIXED,
  rows: [
    new TableRow({ children: stages.map((s, i) => cell([new TextRun({ text: (i ? '→ ' : '') + s, size: 17, bold: true })], swArr[i], { align: AlignmentType.CENTER, valign: VerticalAlign.CENTER, fill: i === 1 || i === 2 ? C.accentSoft : undefined })) }),
    new TableRow({ children: [cell([new TextRun({ text: 'HEAD 3 · getting a video in and running its job to "ready", whatever the phone does meanwhile', bold: true, size: 18, color: 'FFFFFF' })], W, { span: stages.length, fill: C.accent, align: AlignmentType.CENTER, borders: { top: NB, bottom: NB, left: NB, right: NB } })] }),
  ],
}));
body.push(P('It comes after the database (Head 2) and before every processing stage (Heads 4–6). Nothing is searchable until its job reaches "ready".', { run: { size: 19, color: C.muted }, before: 80 }));

body.push(LABEL('What · Why · Result'));
const t3 = Math.floor(W / 3);
body.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: [t3, t3, W - 2 * t3], layout: TableLayoutType.FIXED,
  rows: [
    new TableRow({ children: ['What we did', 'Why', 'Result'].map((h, i) => cell(h, i < 2 ? t3 : W - 2 * t3, { fill: C.head, bold: true, size: 18 })) }),
    new TableRow({ children: [
      cell('Measured every stage on two phones with one harness. Moved the job to WorkManager with a notification. Proved each stage safe to rerun. Stopped copying the video. Added a duplicate check and "do not retry" errors.', t3),
      cell('A clip only counts once it is "ready", and people do not keep an app open for minutes. Before, a job stalled when another app was in front, and Android killed the app for heavy background work.', t3),
      cell('An 8-minute clip finishes in **4 min 10 s** with the screen off. **12 of 12** kills on two phones resumed with identical output. An hour of video costs **126 MB** instead of 9.2 GB. The same file twice is refused.', W - 2 * t3),
    ] }),
  ],
}));

body.push(LABEL('Numbers to remember'));
const nums = [
  ['0.85–4.53', 'minutes of work per minute of video, app in front: Pixel 0.85–1.57, Infinix 1.80–3.22, A32 2.69–4.53', 'E1, E2'],
  ['4 min 10 s', 'for an 8-minute clip with the app in the background, screen off, deep Doze (Pixel)', 'E5'],
  ['12 of 12', 'kills mid-stage (9 Infinix, 3 Pixel) resumed at the next stage, same rows', 'E4'],
  ['126 MB', 'of app storage per hour of camera video since reading in place (was 9.2 GB)', 'E7'],
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
  ['Jobs run as WorkManager long-running work with a `dataSync` foreground service and a "Video n of m" notification (EYKO-44).', 'The in-app thread stalled with another app in front (21.2 min instead of about 13) and was killed for "excessive cpu" after 26 min in the background. With the service, 55 min of video ran 96 min in the background without a kill.', 'E5, E8'],
  ['One job per video, ten stages in a fixed order, the stage saved after each one.', 'A crash costs only the stage it hit. Every stage deletes or rebuilds its own rows first, so running it twice gives the same result.', 'E4'],
  ['Errors that can never succeed fail at once (`PermanentFailure`); the rest get 3 attempts.', 'An unreadable or deleted file used to waste three attempts.', 'E4, E7'],
  ['Read the picked video in place; copy only if the phone will not keep the read permission (EYKO-126).', 'The copy was 98 % of the storage cost and the reason for the 500 MB limit.', 'E7'],
  ['Refuse a file whose SHA-256 is already saved (EYKO-71).', 'The same file was saved twice on the Pixel. The hash costs 17–22 ms.', 'E7'],
  ['Pick with the system file picker and ask for media location (EYKO-127).', 'The photo picker strips the recording place from every file.', 'E6'],
]));

body.push(LABEL('Weak spots: say these before they find them'));
const weak = [
  ['Partly', 'The Samsung A32 ran the stage timings (17 Nov) but not a background job or a queue. EYKO-168 covers its background check and Samsung\'s "Sleeping apps" rule.'],
  ['Partly', 'On the Infinix, a job saved before a reboot only starts when the app is opened. The Pixel starts it by itself. Likely the maker\'s auto-start control, not proven.'],
  ['Open', 'Faster models with the same captions (E2) are not measured: EYKO-121 has not started.'],
  ['Partly', 'Battery per minute of video is measured on the Pixel only, with the screen on (18–24 mAh). The Infinix runs were on the charger.'],
];
body.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: [1300, W - 1300], layout: TableLayoutType.FIXED,
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
  ['Question', null, 'Does a picked video reliably reach "ready", and at what cost?', 'Intake was built in October (copy, metadata, one job, ten stages, resume, 3 retries) but had no evidence. The supervisor questions asked about kills, the app in the background, duplicates, bad files, time per stage, battery and queues.', null],
  ['Rule set before testing', null, 'Same output, real clips, one harness', 'Every speed-up must give identical rows. Every phone run uses the two kit clips (Ego4D cannot be shared). One harness (`run-head3.ps1`) records stage times, copy time, battery and heat as CSV, so the phones are compared the same way.', null],
  ['Baseline · 20 Oct', 'bad', 'The job stalled with another app in front', 'On the Pixel, the old build took about 1.4 min per minute of video. One 8-minute clip took 21.2 min instead of about 13 because another app was in front: the job only ran while the app was.', 'E5'],
  ['Test · 5 Nov · EYKO-84', 'bad', '`latest` was the slowest stage on the Infinix', 'Two 75 s clips: `latest` took 42 s and 136 s. It looked worse than linear; later timing showed it is one crop vector per sighting (EYKO-64).', 'E1, E10'],
  ['Fix · 10 Nov · EYKO-71', 'ok', 'The same file can no longer be added twice', 'The app takes a SHA-256 while reading and refuses a match ("This video is already saved"). The free space is checked before a copy, with a 200 MB reserve.', 'E7'],
  ['Test · 10–11 Nov · EYKO-116, 119', 'ok', 'Every stage is safe to run again', 'All ten stages ran twice in a row and gave the reference result (10 of 10); five crashed half-way and recovered (5 of 5). A planted bug was caught. Real kills: 9 on the Infinix, 3 on the Pixel, all resumed with the same rows. Two errors now fail at once instead of 3 times.', 'E4'],
  ['Test · 11 Nov · EYKO-64', 'ok', 'The Pixel needs half the Infinix\'s time; `latest` is linear', 'Pixel 0.87 and 1.33 min of work per minute of video, Infinix 1.8 and 3.4. `latest` costs 0.23–0.25 s per sighting on the Pixel and 0.80–1.02 s on the Infinix.', 'E1'],
  ['Limit found · 11 Nov', 'bad', 'Android killed the app for heavy background work', 'Without WorkManager: "excessive cpu ... limit=2" after 26 min of work in the background on the Infinix.', 'E5'],
  ['Build · 12–15 Nov · EYKO-44', 'ok', 'Jobs finish with the app closed', 'WorkManager long-running work with a foreground notification. Infinix: 5-min clip ready in 5.5 min in front, 6.7 with five other apps, 5.4 after a swipe; 55 min of video in 96 min in the background, never killed. Pixel: resumes by itself 47 s after a reboot.', 'E5'],
  ['Test · 12 Nov · EYKO-118', 'ok', '14 awkward files: no crash', 'HEVC, HDR, portrait, variable frame rate, no audio and no metadata all work. Damaged files and `.mkv` are refused before a job is made. Three bugs found: no recording place, `.avi` listed but unreadable, a vague error.', 'E6'],
  ['Change · 13 Nov · EYKO-126, 127', 'ok', 'Read in place, keep the place', 'No copy: 126 MB per hour of video instead of 9.2 GB, and no 500 MB limit (743 MB accepted). Deleting the gallery file later does not break search. The system file picker plus the media-location permission stores the recording place.', 'E6, E7'],
  ['Test · 14–15 Nov · EYKO-117, 123', 'ok', 'One harness, two phones, queues and back-fill', 'Same clips, 3 runs each: Pixel 63.9 and 110.2 s, Infinix 138.1 and 233.5 s. A queue of 9–10 videos ran back to back with no failure. Back-fill re-ran only the missing stages.', 'E1, E2, E3'],
  ['Improvement · 15 Nov', 'ok', 'Frame splitting about 3× faster on the Pixel, same JPEGs', 'Splitting frames was the biggest stage on the Pixel (26.7 s). Copying pixel rows in bulk and asking the decoder for full speed took it to 7.9–10.4 s, with identical JPEG files.', 'E11'],
  ['Test · 15 Nov · EYKO-85', 'ok', 'An 8-minute clip in 4 minutes in the background', 'Screen off, deep Doze, with or without Battery Saver: ready in 4 min 10 s and 4 min 4 s. Only Extreme Battery Saver pauses the app.', 'E5'],
  ['Research · 16–17 Nov · EYKO-122, 120', 'ok', 'Android\'s rules, and a faster `latest` with the same output', 'Android 15+ allows a `dataSync` service 6 h a day. `latest` now decodes each frame once and relinks only from the new video\'s time: for 4,000 sightings 7.5 million comparisons became 73 thousand, same links.', 'E8, E9, E10'],
  ['Still open', null, 'What comes next', 'The A32 background check (EYKO-168). Faster models with the same captions (EYKO-121). Fewer crop vectors in `latest`, which changes the output and needs a quality score. `small_objects` not profiled. Infinix auto-start after a reboot. The file-type list (drop `.avi`).', null],
];
steps.forEach((s, i) => {
  const [kind, tone, title, text, show] = s;
  const col = tone === 'bad' ? C.bad : tone === 'ok' ? C.ok : C.accent;
  const right = [
    new Paragraph({ children: [new TextRun({ text: kind.toUpperCase(), size: 15, bold: true, color: C.muted, characterSpacing: 20 })], spacing: { after: 40 }, keepNext: true }),
    new Paragraph({ children: runs(title, { size: 22, bold: true }), spacing: { after: 60 }, keepNext: true }),
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
  ['A1', 'A', 'What happens if the app is killed in the middle of a stage, on a real phone?', 'Answered',
    'It resumes at the stage after the last saved one, in a new process, with the same output. We force-stopped the app **12 times on two phones** with the real models: 9 on the Infinix (inside `scene`, `small_objects`, `embed_texts`) and 3 on the Pixel (inside `split`, `scene`, `latest`). Every run reached "ready" with the uninterrupted run\'s numbers and all ten link counts at 0.',
    'E4 · `docs/results/2026-11-09-storage-and-crash.md` (Part 3) · `docs/results/2026-11-11-stages-safe-to-rerun.md`',
    'These were clean `force-stop` kills, not a power-manager or out-of-memory kill. `filter`, `dedup`, `embed_images`, `link` and `finish` were not killed on a phone; they last under 3 s and are covered by the run-twice tests (10 of 10).', 'Done: EYKO-116 Part 3, EYKO-119'],
  ['A2', 'A', 'What if the app is closed, or another app is in front?', 'Answered',
    'The job keeps going. Since EYKO-44 it runs as Android background work with a notification. On the Pixel an 8-minute clip was ready in **4 min 10 s** with the app in the background, the screen off and the phone in deep Doze (4 min 4 s with Battery Saver). On the Infinix a 5-minute clip took 5.5 min in front, 6.7 min with five other apps in front and 5.4 min after a swipe from recents. Before, the same kind of clip stalled (21.2 min instead of about 13).',
    'E5 and Figure 3 · `docs/results/2026-11-15-eyko85-background-long-clip.md` · `2026-11-12-eyko44-workmanager-phone-checks.md` · `2026-11-15-eyko44-pixel-checks.md`',
    'Extreme Battery Saver pauses the app completely. After a reboot the Pixel resumes the job by itself; the Infinix waits until the app is opened (likely its auto-start control, not proven). Android 15+ allows the service 6 h a day; not reached in any test. The A32 was not run (EYKO-168).', 'Done: EYKO-44, EYKO-85 · Open: EYKO-168'],
  ['A3', 'A', 'What if the same video is added twice?', 'Answered',
    'It is refused with "This video is already saved (recorded …)". The app takes the file\'s SHA-256 while reading it and checks it against every saved video. On the Pixel the second add of a clip left no row, no job and no folder. The hash costs 17–22 ms per clip.',
    'E7 · `docs/results/2026-11-10-eyko-71-duplicates-and-space.md` · on-device `VideoCaptureTest` 4 of 4',
    'Only identical bytes are caught: a trimmed or re-encoded copy is a new video. Videos saved before 10 Nov have no hash. A file added once with and once without the media-location permission gives two hashes (the place bytes are zeroed without it).', 'Done: EYKO-71'],
  ['A4', 'A', 'What about awkward files: HEVC, HDR, portrait, variable frame rate, no GPS, damaged, very large?', 'Answered',
    'No crash on 14 test files, on two phones. HEVC, HDR, portrait, variable frame rate, no audio and no metadata all reach "ready". HDR frames have normal colour and portrait frames are stored upright. A damaged file and `.mkv` are refused with a clear message before any job is made. Since reading in place, a 528 MB file is accepted (212 s of video processed in 129 s on the Pixel).',
    'E6 · `docs/results/2026-11-12-head3-bad-inputs.md` · `2026-11-15-head3-intake-two-phones.md` · `2026-11-13-read-from-gallery.md`',
    '`.avi` failed on both phones (bug 2), so it was dropped on 17 Nov and is now refused at once with a clear message; 3gp, mkv and webm were added and reach "ready" on the Pixel (E9). An audio-only file cannot be offered by the picker, so it was not tried. A file with no recorded time shows the time it was added. No real 4K or very long camera clip was tried.', 'Done: EYKO-118, 123, 126, 127'],
  ['A5', 'A', 'Where do the 500 MB limit and the four file types come from?', 'Answered',
    '500 MB was a copy limit, and it is gone on the normal path: the app now reads the video in place (EYKO-126). It was only **1.5 to 4 minutes** of phone video (3.5 min at the Pixel\'s 20 Mbps). For file types, Android\'s own list covers mp4, 3gp, mkv and webm (H.264, HEVC, VP8, VP9, AV1); it does not list `.avi` or `.mov`. `.mov` works on both phones in practice; `.avi` fails on both.',
    'E9 · `docs/research/2026-11-16-head3-background-and-limits.md` (Part 2)',
    'The 500 MB limit stays only on the copy fallback (when the phone will not keep the read permission); EYKO-122 suggests a free-space margin instead. The new type list (drop avi; add 3gp, mkv, webm) was built on 17 Nov on the phone and the laptop and checked on the Pixel with one file of each. Our ffmpeg-made 3gp was indexed by Android as mp4; a phone-recorded 3gp was not tried.', 'Done: EYKO-122, 126; type list 17 Nov'],
  ['B1', 'B', 'Which stage takes the time, on every phone, same build?', 'Answered',
    'Three phones, same clips. On the Infinix `latest` leads (44 of 138 s, 111 of 234 s). On the A32 `small_objects` leads clip 1 (68 of 203 s) and `latest` clip 2 (147 of 339 s); the model stages are 74–83 % of its time. On the Pixel, frame splitting led clip 1 (26.7 of 64 s) and `latest` clip 2 (45 of 110 s). On 15 Nov splitting got about 3× faster on the Pixel (7.9–10.4 s, same JPEGs).',
    'E1 and Figure 1 · `docs/results/2026-11-15-head3-intake-two-phones.md` · `2026-11-14-head3-intake-infinix.md` · `2026-11-17-head3-intake-a32.md` · E11',
    'The builds differ: the Infinix still copied the file, the Pixel ran before the faster split, the A32 after it. The model stages did not change between them, so their comparison holds; frame splitting does not compare across phones. All three keep the same frames and sightings on the same clip.', 'Done: EYKO-117, 123, 64; A32 runs 17 Nov'],
  ['B2', 'B', 'How many minutes of work per minute of video on a modest phone?', 'Answered',
    'On the slowest phone, the A32: **2.69–2.77** for clip 1 and **4.46–4.53** for clip 2, with the app in front (a 75 s clip is ready in 3.4 to 5.7 min). On the Infinix: **1.80–1.89** and **3.02–3.22**; **2.57** for a queue of ten; 1.75 in the background over 55 min of video. The Pixel needs 0.85–0.90 and 1.23–1.57. Clip 2 costs more because it keeps more frames and has 2.5× the sightings, not because the phone is hotter.',
    'E2 and Figure 2 · `docs/results/head3/run_summary.csv` · `docs/results/2026-11-17-head3-intake-a32.md`',
    'The A32 ran on the cable with the app in front only: no queue, no background run and no battery figure on it. Two clips of 75 s each: other footage keeps more or fewer frames.', 'Done: EYKO-117, 123; A32 runs 17 Nov'],
  ['B3', 'B', 'What does a minute of video cost in battery and heat?', 'Partly',
    'On the Pixel, unplugged, screen on: **18–24 mAh per minute of video**, about 0.4–0.5 % of its battery. An hour of footage would cost roughly a quarter of a charge. Battery temperature stayed at 30.6–36.3 °C on the Pixel; the Infinix reached 38.6 °C in a queue and 39.4 °C over 96 min in the background.',
    'E2 · `docs/results/2026-11-15-head3-intake-two-phones.md` (B3)',
    'The screen\'s share is inside the figure and was not measured apart. The Infinix runs were on the charger, so they have no battery figure. Background battery on the Pixel was only whole percent (51 to 49 % for 8 min of video).', 'EYKO-123'],
  ['B4', 'B', 'Ten videos queued: how long until the last one is ready?', 'Answered',
    'On the Infinix, 10 videos (12.5 min of video) were all ready after **32 min**; on the Pixel, 9 videos (11.2 min) after **15.5 min**. No failures, and no idle gap: the wall time is within 3 % of the stage time added up. The videos run one after another.',
    'E3 · `docs/results/head3/run_summary.csv` (S2)',
    'The Pixel had 9 videos, not 10: one test copy had the same bytes as an earlier one and was refused (a setup mistake). The app was in front. In the background, four movie pieces (55 min) were ready after 96 min on the Infinix.', 'Done: EYKO-117, 123, 44'],
  ['B5', 'B', 'How long does a large file take to get in, and what if storage is full?', 'Partly',
    'Getting the file in is under 1 % of the work. The old copy of a 188 MB clip took 966 ms on the Infinix. Since EYKO-126 nothing is copied: the Pixel reads a clip in place in 448–1,036 ms (743 MB in 3.6 s). Storage: the copy path checks the size plus a 200 MB reserve before it starts, checks again every 8 MB, and turns a disk-full error into a clear message with no half-written file.',
    'E7 · `docs/results/2026-11-14-head3-intake-infinix.md` (S3) · `2026-11-10-eyko-71-duplicates-and-space.md`',
    'The full-storage cases are proven by JVM tests (`VideoCopyTest`, 7 of 7), not on a phone that was really full. The 200 MB reserve is a first value, not measured. With reading in place the app needs about 126 MB per hour of video.', 'EYKO-71, 117, 126'],
  ['C1', 'C', 'Does a resumed stage give the same rows as a clean run?', 'Answered',
    'Yes. A test runs each of the ten stages twice and compares every table, every vector and every file with a clean run: **10 of 10** identical. Five stages crashed half-way and ran again: 5 of 5 identical. When we removed one line on purpose, the test failed. On the Pixel, three real kills ended with the clean run\'s numbers and the same captions fingerprint.',
    'E4 · `docs/results/2026-11-11-stages-safe-to-rerun.md` · `VideoRerunSafetyTest`',
    'Stand-in models in the test, real models in the kills. Re-run on 17 Nov after the EYKO-120 change: 17 of 17 on the Pixel.', 'Done: EYKO-119, 120'],
  ['C2', 'C', 'Does a retry waste three attempts on a file that can never work?', 'Answered',
    'Not any more. Errors that cannot succeed are `PermanentFailure` and fail on the first attempt: no frame can be read, the link check finds broken rows, or the gallery file was deleted mid-job (1 attempt, clear message, on the Pixel). Other errors keep 3 attempts.',
    'E4, E7 · `docs/results/2026-11-11-stages-safe-to-rerun.md` (C2) · `2026-11-13-read-from-gallery.md` (check 4)',
    'Only three cases are classed permanent so far. A permanently failed video still shows Retry, which fails again at once. An `Error` (out of memory) skips the handler; the job is re-queued at the next app start.', 'Done: EYKO-119, 126'],
  ['C3', 'C', 'When a new stage is added, do old videos catch up?', 'Partly',
    'Yes, in a controlled check on both phones. Setting a finished video\'s saved stage back to `latest` re-ran only `finish`; setting it to `link` re-ran `latest` and `finish` (30.6 s on the Pixel). No other stage ran.',
    'E3 · `docs/results/2026-11-15-head3-intake-two-phones.md` (S4) · `2026-11-14-head3-intake-infinix.md` (S4)',
    'This sets the saved stage back by hand; no real new stage has been shipped to a phone full of old videos yet. One video per phone.', 'EYKO-117, 123'],
  ['D1', 'D', 'Why an in-app thread and not WorkManager?', 'Answered',
    'We switched to WorkManager (EYKO-44). The in-app thread stalled and was killed in the background. Now the job is long-running work with a `dataSync` foreground service, which is how Android lets work run over 10 minutes. It has held in every test (E5).',
    'E8 · `docs/research/2026-11-16-head3-background-and-limits.md` (Part 1) · E5',
    'Android 15+ gives a `dataSync` or `mediaProcessing` service 6 h a day; opening the app resets it. EYKO-122 recommends `mediaProcessing` on Android 15+, a check that a job stopped by the 6 h limit resumes, and telling Transsion, Xiaomi and Samsung users about their battery settings. None of these is a card yet.', 'Done: EYKO-44, 122'],
  ['E1', 'E', 'Why is `latest` the slowest stage, and can it be faster with the same output?', 'Answered',
    'It computes one MobileCLIP vector per sighting: 0.23–0.25 s each on the Pixel, 0.80–1.02 s on the Infinix, in a straight line. EYKO-120 made it cheaper with identical output. Each frame is now decoded once, not once per object. Relinking compares only from the new video\'s time: for 4,000 sightings, **7.5 million → 73 thousand** comparisons and 4,000 → 0–3 row writes.',
    'E10 and Figure 4 · `docs/results/2026-11-17-latest-stage-profile.md` · `2026-11-11-pixel-kit-clips-timing.md`',
    'The model run per sighting is still the main cost. Cutting it means fewer crops, which changes the output and needs a quality score first. Batching the crops was slower (0.80–0.86×). Phone time on a large library was not measured. `small_objects` was not profiled (no YOLOE on the laptop).', 'Done: EYKO-120 · output-changing options: lead'],
  ['E2', 'E', 'Can the models run faster (threads, int8, NNAPI) with the same captions?', 'Open',
    'Not measured yet. The card is written: each scene model timed on the laptop with thread counts, graph optimisation and int8, with captions identical on at least 95 % of frames.',
    'Nothing yet',
    'Laptop first; only winners go to the phone, each as its own card.', 'EYKO-121'],
];

body.push(LABEL('All questions at a glance', { before: 0 }));
body.push(grid([700, W - 700 - 1300 - 2000, 1300, 2000], ['#', 'Question', 'Status', 'Closes with'],
  Q.map((q) => [q[0], q[2], [chip(q[3])], q[7]])));
body.push(P('Groups: A = does intake survive real use · B = time, battery and size · C = correctness of reruns · D = background design · E = making it faster.', { run: { size: 17, color: C.muted }, before: 80 }));

const GROUPS = { A: 'A · Does intake survive real use?', B: 'B · Time, battery and size', C: 'C · Reruns and retries', D: 'D · Background design', E: 'E · Making it faster' };
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
        new TextRun({ text: id + '   ', bold: true, size: 20, color: C.accent }), ...runs(question + '   ', { bold: true, size: 20 }), chip(status),
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
body.push(P('Open this part when the professor asks "show me". Each item says in one line what it proves, then the table or graph, then the file it came from. Times are in seconds unless shown.', { run: { color: C.muted } }));

function ev(id, title, shows) {
  body.push(H2(`${id} · ${title}`));
  body.push(P([new TextRun({ text: 'What it shows: ', bold: true, size: 20 }), ...runs(shows, { size: 20 })], { after: 100, keepNext: true }));
}

ev('E1', 'Seconds per stage on three phones, same clips (14–17 Nov)', 'The Pixel is 2–4× faster on every model stage; the A32 is the slowest, about 1.5× the Infinix. `latest` is the largest cost on the Infinix and on the A32\'s clip 2; `small_objects` on the A32\'s clip 1.');
body.push(grid([2038, 1266, 1266, 1266, 1266, 1266, 1270], ['Stage (median of 3 runs, plugged)', 'Clip 1 Infinix', 'Clip 1 Pixel', 'Clip 1 A32', 'Clip 2 Infinix', 'Clip 2 Pixel', 'Clip 2 A32'], [
  ['copy (Infinix) / read in place', '0.8', '0.6', '1.1', '0.9', '0.6', '1.2'],
  ['split_frames', '21.7', '**26.7**', '22.7', '22.0', '**26.8**', '23.9'],
  ['split_audio', '9.1', '5.5', '12.4', '11.3', '5.3', '12.7'],
  ['filter', '2.1', '0.6', '3.0', '1.8', '0.6', '3.4'],
  ['dedup', '10.5', '2.4', '11.4', '14.3', '3.5', '15.8'],
  ['scene', '17.0', '4.7', '26.0', '25.8', '8.0', '40.5'],
  ['small_objects', '32.1', '10.9', '**68.2**', '45.7', '20.3', '93.8'],
  ['embed_images', '0.0', '0.0', '0.0', '0.0', '0.0', '0.0'],
  ['embed_texts', '1.6', '0.1', '0.6', '1.4', '0.2', '0.7'],
  ['**latest**', '**44.0**', '12.4', '57.6', '**111.1**', '**44.9**', '**147.3**'],
  ['**Added up**', '**138.1**', '**63.9**', '**203.0**', '**233.5**', '**110.2**', '**339.2**'],
], { firstColBold: true, highlight: (r) => r[0] === '**latest**' }));
figure('head3-stage-times.png', '**Figure 1.** Median seconds per stage, S1 (one clip at a time, app in front), Infinix X670, Pixel 9 Pro XL and Samsung A32 (SM-A325F). Clip 1 keeps 10 frames and 53–54 sightings; clip 2 keeps 16 frames and 134 sightings, on every phone.');
body.push(SRC('docs/results/head3/stage_times.csv · docs/results/2026-11-15-head3-intake-two-phones.md · docs/results/2026-11-14-head3-intake-infinix.md · docs/results/2026-11-17-head3-intake-a32.md'));
body.push(P('**Builds:** Infinix 5a192c7 (still copied the file), Pixel a915c8d (before the faster split), A32 e4f2bd7 (after it, and after the EYKO-120 relink change). The model stages are comparable across phones; frame splitting is not.', { run: { size: 18, color: C.muted } }));
body.push(P('**Why clip 2 costs more:** the cost per unit is the same on both clips (`latest` about 0.83 s per sighting and `scene` about 1.7 s per frame on the Infinix). Clip 2 simply has more kept frames (16 against 10) and more sightings (134 against 53).', { run: { size: 20 } }));

ev('E2', 'Minutes of work per minute of video, every run (14–17 Nov)', 'Under 1 on the Pixel for clip 1, 1.2–1.6 for clip 2; the Infinix needs about twice that and the A32 about three times (2.69–4.53). Battery on the Pixel: 18–24 mAh per minute of video.');
figure('head3-work-per-minute.png', '**Figure 2.** One dot per harness run. S1 = one clip, app in front (the Pixel\'s clip 1 includes three unplugged runs); S2 = a queue of 9 (Pixel) or 10 (Infinix) videos. The A32 (SM-A325F) ran S1 only.');
body.push(grid([3238, 3200, 3200], ['Run (Pixel, unplugged, screen on)', 'Charge used', 'Per minute of video'], [
  ['7 (clip 1)', '30.0 mAh', '24.2 mAh'],
  ['8 (clip 1)', '25.0 mAh', '20.1 mAh'],
  ['9 (clip 1)', '22.5 mAh', '18.1 mAh'],
], { firstColBold: true }));
body.push(SRC('docs/results/head3/run_summary.csv · docs/results/2026-11-15-head3-intake-two-phones.md (B3) · charge counter from dumpsys battery'));

ev('E3', 'A queue of ten, and back-fill (14–15 Nov)', 'Videos run back to back with no failures and no idle time. Back-fill runs only the missing stages.');
body.push(grid([3238, 3200, 3200], ['', 'Infinix (10 videos)', 'Pixel (9 videos)'], [
  ['Video in the queue', '747.0 s', '672.5 s'],
  ['Stage time added up', '1,918.0 s', '908.8 s'],
  ['Work per video second', '2.57', '1.35'],
  ['Wall time, first video in to last ready', '**1,920 s (32 min)**', '**931 s (15.5 min)**'],
  ['Copy / read per video', '704–1,780 ms (copy)', '615–1,036 ms (read)'],
  ['Unfinished / highest temperature', '0 / 38.6 °C', '0 / 36.0 °C'],
  ['Back-fill: saved stage set to `latest`', 'only `finish` ran', 'only `finish` ran'],
  ['Back-fill: saved stage set to `link`', '—', '`latest`, `finish` ran (30.6 s)'],
], { firstColBold: true }));
body.push(SRC('docs/results/head3/run_summary.csv (S2, S4) · docs/results/2026-11-15-head3-intake-two-phones.md · docs/results/2026-11-14-head3-intake-infinix.md'));

ev('E4', 'Kills, reruns and retries (10–11 Nov)', 'Every killed job resumed at the next stage and ended with the clean run\'s numbers. Running any stage twice gives identical tables.');
body.push(grid([1700, 1700, 2238, 4000], ['Phone', 'Killed inside', 'Runs', 'Result'], [
  ['Infinix X670', '`scene`', '3', 'resumed at `scene` in a new process, ready, link counts all 0'],
  ['Infinix X670', '`small_objects`', '3', 'same'],
  ['Infinix X670', '`embed_texts`', '3', 'same'],
  ['Pixel 9 Pro XL', '`split`', '1 (K1)', 'resumed at `split` (0 frames saved), ready, link counts 0'],
  ['Pixel 9 Pro XL', '`scene`', '1 (K2)', 'resumed at `scene` (224 frames saved), ready, link counts 0'],
  ['Pixel 9 Pro XL', '`latest`', '1 (K3)', 'resumed at `latest` (0 sightings saved), ready, link counts 0'],
], { firstColBold: true }));
body.push(P('**Same numbers after every kill:** clip 1 gives 10 kept frames, 6 objects and 53 sightings on the Infinix; on the Pixel 224 frames, 10 kept, 54 sightings (30 latest) and the same captions fingerprint (`f83b795c…`). Job attempts stayed 0: a kill is not counted as a failure.', { run: { size: 20 }, before: 100 }));
body.push(grid([4638, 2500, 2500], ['Test (`VideoRerunSafetyTest`, Pixel)', 'Result', 'Card'], [
  ['Each of the 10 stages run twice gives the reference result', '**10 of 10**', 'EYKO-119'],
  ['Stage crashes half-way, runs again: dedup, scene, small_objects, embed_texts, latest', '5 of 5', 'EYKO-119'],
  ['Planted bug (small_objects without its clean-up line)', 'test fails, as it should', 'EYKO-119'],
  ['`PermanentFailure`: unreadable frames, broken links, source deleted', '1 attempt, not 3', 'EYKO-119, 126'],
  ['Re-run after the EYKO-120 change (17 Nov)', 'VideoLatestTest + VideoRerunSafetyTest 17 of 17', 'EYKO-120'],
], { firstColBold: true }));
body.push(SRC('docs/results/2026-11-09-storage-and-crash.md (Part 3) · docs/results/vectors/crash/infinix-2026-11-10-link-check.csv · docs/results/2026-11-11-stages-safe-to-rerun.md · docs/results/eyko119/'));

ev('E5', 'App in front against app in the background (20 Oct – 15 Nov)', 'Since EYKO-44 the job finishes in the background at about the speed it has in front, with the screen off and in deep Doze.');
body.push(grid([2600, 2200, 2200, 2638], ['Run', 'Phone, clip', 'Time to ready', 'Note'], [
  ['Before: in-app thread, another app in front (20 Oct)', 'Pixel, 8-min Ego4D clip', '**21.2 min** (about 13 expected)', 'stalled while the app was not in front'],
  ['Before: in-app thread in the background (11 Nov)', 'Infinix', 'killed', '"excessive cpu … limit=2" after 26 min'],
  ['A: app in front', 'Infinix, 5-min clip', '5.5 min', 'EYKO-44'],
  ['B: five other apps in front', 'Infinix, 5-min clip', '6.7 min', 'one process, never killed'],
  ['C: swiped from recents', 'Infinix, 5-min clip', '5.4 min', 'same process before and after'],
  ['Four movie pieces, app never reopened', 'Infinix, 55 min of video', '**96 min**', 'no kill, all link counts 0'],
  ['Home, screen off, deep Doze', 'Pixel, 8-min clip', '**4 min 10 s**', 'EYKO-85'],
  ['Same, Battery Saver on', 'Pixel, 8-min clip', '4 min 4 s', 'same output'],
  ['Extreme Battery Saver', 'Pixel', 'paused', 'app suspended by the system'],
  ['Reboot mid-job', 'Pixel / Infinix', 'resumed by itself / only when opened', 'resumed at the stage after the saved one'],
], { firstColBold: true, highlight: (r) => r[2] === '**4 min 10 s**' }));
figure('head3-background.png', '**Figure 3.** Minutes from adding a clip to "ready", app in front and in the background. Each panel is one clip on one phone, so the panels are not compared with each other.');
body.push(SRC('docs/results/2026-10-20-ego4d-baseline.md · 2026-11-12-eyko44-workmanager-phone-checks.md · 2026-11-15-eyko44-pixel-checks.md · 2026-11-15-eyko85-background-long-clip.md'));

ev('E6', 'Fourteen awkward files on two phones (12 and 15 Nov)', 'No file crashed the app. The good ones reach "ready"; the unreadable ones are refused before a job is made.');
body.push(grid([2200, 2800, 3100, 1538], ['File', 'Infinix (12 Nov, copy build)', 'Pixel (15 Nov, read in place)', 'Kept (Pixel)'], [
  ['B1 H.264 control', 'OK, no GPS', 'OK, no GPS', '3 of 5'],
  ['B2 HEVC 8-bit', 'OK', 'OK', '2 of 5'],
  ['B3 HEVC 10-bit HDR', 'OK', 'OK, normal colour (EYKO-126)', '3 of 5'],
  ['B4 portrait', 'OK', 'OK, frames upright 360×640 (EYKO-126)', '2 of 5'],
  ['B5 variable frame rate', 'OK', 'OK', '2 of 4'],
  ['B6 no metadata', 'OK, add time used', 'OK, says the file has no time', '3 of 5'],
  ['B7 damaged', 'refused, vague message', 'refused: "damaged or a format this phone cannot read"', '—'],
  ['B8 audio only', 'not offered by the picker', 'not offered by the picker', '—'],
  ['B9 no audio', 'OK', 'OK', '3 of 5'],
  ['B10a .mov', 'OK, no GPS', 'OK, **place stored**', '3 of 5'],
  ['B10b .m4v', 'OK', 'OK', '3 of 5'],
  ['B10c .avi', 'refused (listed as accepted: bug)', 'refused, the same clearer message', '—'],
  ['B11 .mkv', 'refused, clear', 'refused, clear', '—'],
  ['B12 528 MB', 'refused (500 MB limit)', '**accepted**, 212 s of video in 129 s', '12 of 65'],
], { firstColBold: true }));
body.push(P('**Recording place:** the photo picker hands the app the file with its place zeroed. Since EYKO-127 the app uses the system file picker and asks for the media-location permission: the kit clip is stored at 33.6562, 73.0172, as in the file. With the permission refused, the video is still added, without a place.', { run: { size: 20 }, before: 100 }));
body.push(SRC('docs/results/2026-11-12-head3-bad-inputs.md · 2026-11-15-head3-intake-two-phones.md · 2026-11-13-read-from-gallery.md · 2026-11-13-keep-recording-place.md · docs/results/head3/bad-inputs/'));

ev('E7', 'Getting the file in: copy, read in place, duplicates, space (10–15 Nov)', 'Getting the file in is under 1 % of the work. Reading in place removed the copy that was 98 % of the storage.');
body.push(grid([3638, 3000, 3000], ['', 'Before (copy)', 'Now (read in place, EYKO-126)'], [
  ['Getting a 186–188 MB clip in', '429–1,171 ms (Infinix); 947–1,099 ms (Pixel)', '448–1,036 ms (Pixel)'],
  ['743 MB clip (4 min 58 s)', 'refused over 500 MB', 'read in 3.6 s, ready in 2 min 53 s'],
  ['App storage per hour of camera video', 'about 9.2 GB (calculated)', '**about 126 MB** (measured clip scaled to an hour)'],
  ['Gallery file deleted after "ready"', 'not affected (own copy)', 'search still works'],
  ['Gallery file deleted mid-job', 'not affected', 'fails at once, 1 attempt, clear message'],
  ['Same file twice (EYKO-71)', 'refused; hash 17–22 ms in a 107–208 ms copy', 'refused (hash of the bytes read)'],
  ['Not enough space (EYKO-71)', 'refused before copying (size + 200 MB); checked every 8 MB', 'nothing to copy'],
], { firstColBold: true, highlight: (r) => r[0].startsWith('App storage') }));
body.push(SRC('docs/results/2026-11-10-eyko-71-duplicates-and-space.md · 2026-11-13-read-from-gallery.md · 2026-11-14-head3-intake-infinix.md (S3) · 2026-11-11-pixel-kit-clips-timing.md · VideoCopyTest 7 of 7'));

ev('E8', 'What Android allows a long video job (research, 16 Nov)', 'Long-running WorkManager work with a foreground service is the Android way to run work over 10 minutes; Android 15+ caps it at 6 h a day.');
body.push(grid([2600, 4200, 2838], ['Option', 'Limit (Android documentation)', 'What we measured'], [
  ['In-app thread (before EYKO-44)', 'No protection; a busy background process can be killed', 'killed after 26 min; stalled with another app in front'],
  ['WorkManager, plain worker', 'Doze stops it; 10 to 20 min per window by standby bucket', 'fallback only; ran once at the end of a queue'],
  ['**WorkManager + `dataSync` foreground service (now)**', 'Android 12+: cannot start from the background. Android 15+: 6 h in 24 h, reset when the app is opened', '**works in background, after a swipe, in deep Doze**'],
  ['`mediaProcessing` service (Android 15+)', 'Same 6 h, counted separately; describes our work better', 'not tried'],
  ['Phone makers (Samsung, Xiaomi, Transsion)', 'Extra battery rules on top (dontkillmyapp.com)', 'Infinix: no start after reboot until opened'],
  ['Extreme Battery Saver (Pixel)', 'Pixel setting', 'app paused completely'],
], { firstColBold: true, highlight: (r) => r[0].includes('(now)') }));
body.push(P('**6 h a day in video:** about 205 min of video on the Infinix (1.75 min of work per minute) and about 690 min on the Pixel (0.52).', { run: { size: 20 }, before: 100 }));
body.push(SRC('docs/research/2026-11-16-head3-background-and-limits.md (Part 1, every claim linked to its source)'));

ev('E9', 'File types and the 500 MB limit (research, 16 Nov)', '500 MB was only a few minutes of phone video. Android lists mp4, 3gp, mkv and webm; it does not list avi or mov.');
body.push(grid([2200, 2400, 2400, 2638], ['Type', 'Android lists it', 'Our test', 'Recommendation'], [
  ['.mp4 (H.264, HEVC, AV1)', 'yes', 'works', 'keep'],
  ['.mov', 'no (same layout as mp4)', 'works on both phones', 'keep, tested not guaranteed'],
  ['.m4v', 'no (an mp4 by another name)', 'works', 'keep'],
  ['.avi', '**no**', '**fails on both phones**', '**dropped 17 Nov**: refused at once, clear message (Pixel)'],
  ['.3gp / .mkv / .webm', 'yes', 'mkv refused before 17 Nov; others not tried', '**added 17 Nov**: all three ready on the Pixel'],
], { firstColBold: true }));
body.push(P('**Checked on the Pixel (17 Nov):** 15 s files cut from kit clip 1. VP9 `.webm` and H.264 `.mkv` reach "ready" (3 of 45 frames kept each); our `.3gp` reaches "ready" (2 of 45) but Android indexed it as `video/mp4`, so a phone-recorded 3gp is still untested; the EYKO-118 `.avi` is refused with "Use one of: mp4, mov, m4v, 3gp, mkv, webm". Source: `docs/results/2026-11-17-file-types.md`.', { run: { size: 20 }, before: 100 }));
body.push(grid([3638, 3000, 3000], ['Recording', 'Per minute', '500 MB lasts'], [
  ['Pixel kit clip, 1080p HEVC, 20 Mbps (our file)', '150 MB', '**3.5 min**'],
  ['Pixel 6, 4K30 H.264, 48 Mbps (review)', '360 MB', '1.5 min'],
], { firstColBold: true }));
body.push(SRC('docs/research/2026-11-16-head3-background-and-limits.md (Part 2) · developer.android.com/media/platform/supported-formats'));

ev('E10', '`latest`: where the time goes, and a faster version with the same output (17 Nov)', 'The cost is one MobileCLIP run per sighting. The relink step no longer grows with the square of the library, with identical links.');
body.push(grid([2638, 1750, 1750, 1750, 1750], ['Sightings of one label', 'Comparisons before', 'Comparisons now', 'Rows written before / now', 'Same links'], [
  ['500', '120,659', '9,404', '500 / 1', 'yes'],
  ['1,000', '482,264', '18,980', '1,000 / 0', 'yes'],
  ['2,000', '1,900,987', '37,366', '2,000 / 1', 'yes'],
  ['4,000', '**7,484,821**', '**73,494**', '4,000 / 3', 'yes'],
], { firstColBold: true, highlight: (r) => r[0] === '4,000' }));
body.push(P('**Per object on the laptop:** decoding the frame once per frame instead of once per object took 46.2 → 6.8 ms per 12-box frame (about 1 % of `latest`). The crop vector is 260 ms. Batching crops through MobileCLIP was slower (0.80–0.86×), so it was not ported. On the phone: 0.23–0.25 s per sighting on the Pixel, 0.80–1.02 s on the Infinix.', { run: { size: 20 }, before: 100 }));
figure('head3-latest-profile.png', '**Figure 4.** `latest` time against sightings, and relink comparisons as the library grows (EYKO-120, drawn by `src/benchmarks/latest_profile.py`).');
body.push(SRC('docs/results/2026-11-17-latest-stage-profile.md · docs/results/latest-profile/latest-profile.json · VideoLatestLinkTest (JVM 123 of 123) · Pixel on-device 17 of 17'));

ev('E11', 'Frame splitting about 3× faster on the Pixel (15 Nov)', 'Splitting frames went from 28.8–32.2 s to 7.9–10.4 s on the 75 s kit clip, with byte-identical JPEGs. On the A32 the decoder itself is 89 % of the split.');
body.push(grid([3638, 3000, 3000], ['', 'Before', 'After (commit d93c56b)'], [
  ['Split frames, 75 s kit clip, Pixel', '28.8–32.2 s', '**7.9–10.4 s**'],
  ['Same, Samsung A32 (17 Nov)', 'not measured', '24.0–26.4 s (decoding 21.4–22.4 s)'],
  ['Of which: decoding', '18.6–19.6 s', '—'],
  ['Of which: JPEG encoding', '9.0–13.3 s', '—'],
  ['Change', '—', 'bulk pixel-row copy in `toJpeg`; decoder asked for full speed (`KEY_OPERATING_RATE`)'],
  ['Same output?', '—', 'JPEG hash identical (`5866f9ce…`)'],
], { firstColBold: true }));
body.push(SRC('docs/results/2026-11-17-split-frames-faster.md · docs/results/split-timing/a32-2026-11-17-e4f2bd7.txt · commit d93c56b · SplitTimingBenchmarkTest.kt'));

body.push(H2('Limits: how these numbers could mislead'));
[
  'The Samsung A32 (slowest) ran only the stage timings and the split test: no queue, background run or battery figure on it.',
  'The three phones ran three different builds (E1): the model stages are comparable, frame splitting is not.',
  'Two 75 s kit clips for every timing. Footage that keeps more frames or has more objects costs more (clip 2 costs 1.7× clip 1 on the same phone).',
  'The Infinix ran an older build that still copied the file; the Pixel read it in place. The copy is under 1 % of the time, but the builds are not identical.',
  'Most runs were on the charger. Only the Pixel\'s runs 7–9 and EYKO-85 were on battery.',
  'Kills were clean `force-stop` kills, not memory or power-manager kills.',
  'The split speed-up (E11) was not measured on the Infinix, and not on the A32 before it.',
].forEach((t) => body.push(bullet(t)));

// ======================================================================
// PART E
// ======================================================================
body.push(BREAK());
body.push(H1('Part E · Words, gaps, upkeep'));
body.push(H2('Words in plain language'));
body.push(grid([2338, W - 2338], ['Word', 'What it means here'], [
  ['Job', 'One video\'s trip through the ten stages. It saves which stage it reached.'],
  ['Stage', 'One step of the job: split, filter, dedup, scene, small_objects, embed_images, embed_texts, link, latest, finish.'],
  ['Ready', 'All ten stages passed. Only ready videos are searched.'],
  ['WorkManager', 'Android\'s library for work that must finish even if the app is closed or the phone restarts.'],
  ['Foreground service', 'Work Android treats as visible to the person, shown by a notification. It is not killed like hidden background work.'],
  ['`dataSync` / `mediaProcessing`', 'The two foreground service types Android allows for long jobs; Android 15+ gives each 6 h a day.'],
  ['Doze', 'Android\'s deep sleep when the screen is off and the phone is still. Ordinary background work stops.'],
  ['Force-stop', 'Android ending the app at once, as when a person force-closes it.'],
  ['Read in place', 'The app decodes the gallery file through the picker\'s link instead of copying it.'],
  ['SHA-256', 'A fingerprint of the file\'s bytes. Two files with the same fingerprint are the same file.'],
  ['PermanentFailure', 'An error that cannot succeed on retry. The job fails on the first attempt.'],
  ['Back-fill', 'Running only the missing stages on videos made before a new stage existed.'],
  ['Sighting', 'One object seen in one kept frame, with the vector of its own crop.'],
  ['Kit clips', 'Our two 75 s Pixel camera clips used for every phone run.'],
], { firstColBold: true }));

body.push(H2('Open gaps for this Head'));
body.push(grid([800, 3938, 1600, 1100, 2200], ['Gap', 'What is missing', 'Card', 'Severity', 'Resolution'], [
  ['G10', 'Videos only processed while the app was in front; an 8-minute clip stalled.', 'EYKO-44, 85', 'Medium', 'Fixed. WorkManager + foreground service: 8-min clip in 4 min 10 s in the background, screen off (Pixel); 55 min in 96 min (Infinix).'],
  ['G11', 'The same file could be added twice.', 'EYKO-71', 'Low', 'Fixed 10 Nov: SHA-256 while reading, refused with a message.'],
  ['G18', 'Pixel storage: 620 MB free, the app could not be reinstalled.', 'EYKO-83', 'Medium', 'Closed 8 Nov by the owner; every reinstall since has worked. Reading in place (EYKO-126) also stops videos taking double space.'],
  ['—', 'The A32 has run no background job, queue or battery test.', 'EYKO-168', 'Medium', 'Stage timings done 17 Nov (B1, B2).'],
  ['—', 'Infinix: a saved job does not start after a reboot until the app is opened.', 'EYKO-170', 'Low', 'Likely auto-start control; Zara tests it.'],
  ['—', '`.avi` accepted but unreadable; 3gp, mkv, webm not accepted.', 'lead (17 Nov)', 'Low', 'Fixed 17 Nov on phone and laptop (avi out; 3gp, mkv, webm in); Pixel: webm, mkv, 3gp ready, avi refused with a clear message.'],
  ['—', '`mediaProcessing` type and the 6 h timeout are not handled on purpose.', 'EYKO-169', 'Low', ''],
  ['—', 'Model runtime options and int8 (E2).', 'EYKO-121', 'Medium', ''],
  ['—', '`small_objects` not profiled; fewer crops in `latest` changes output.', 'lead', 'Low', ''],
  ['—', 'No way to delete a saved video.', 'EYKO-66', '—', ''],
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
  'Code: `android/…/video/VideoCapture.kt`, `VideoCopy.kt`, `VideoJobs.kt`, `VideoJobWorker.kt`, `VideoPipeline.kt`, `VideoLatest.kt`',
  'Harness: `docs/phone-kit/run-head3.ps1`, `src/benchmarks/head3_intake.py`, `src/benchmarks/head3_compare.py`',
  'Plan and questions: `docs/plans/head-3-research/00-plan.md`',
  'Graphs: `docs/documents/source/figures/head3_intake.py`',
].forEach((t) => body.push(bullet(t)));

// ======================================================================
const doc = new Document({
  creator: 'Eykon', title: 'Head 3 · Video intake',
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
      new TextRun({ text: 'Eykon · Head 3 · Video intake  ·  page ', size: 16, color: C.muted }),
      new TextRun({ children: [PageNumber.CURRENT], size: 16, color: C.muted }),
    ] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = process.argv[2] || path.join(__dirname, '..', 'Head-3-Video-intake.docx');
  fs.writeFileSync(out, buf);
  console.log('wrote', out, buf.length);
});
