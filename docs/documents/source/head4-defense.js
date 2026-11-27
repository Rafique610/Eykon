// Head 4 defense doc (layout and rules: docs/documents/HEAD-DOC-TEMPLATE.md; helpers copied from head3-defense.js).
// Usage: node head4-defense.js  (from this folder; writes ../Head-4-Video-processing.docx)
// Every number comes from a file in docs/results/ named in the Source line under it.
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
body.push(P([new TextRun({ text: 'EYKON  ·  DEFENSE NOTES  ·  HEAD 4 OF THE PIPELINE', bold: true, size: 16, color: C.accent, characterSpacing: 30 })], { after: 80 }));
body.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun('Video processing')] }));
body.push(P('From every frame of a video to the few frames worth describing: pull frames, drop useless ones with plain maths, drop repeats.', { run: { color: C.muted, size: 22 }, after: 200 }));

body.push(grid([2100, W - 2100], null, [
  ['**Last updated**', '27 Nov 2026'],
  ['**Overall status**', 'Built and in use on the Pixel 9 Pro XL. Compared with five existing methods on three data sets, all at the same number of frames. It is **cheaper than evenly spaced frames, with close recall; it is not better**. On long, mostly still video it found the most events of every method (10 of 13) but failed the rule we set before the run. Every frame now stores the sharpness and brightness the filter measured, so any decision can be shown afterwards. Not done: the supervisor\'s "sharpest of every 1/3 s at 30 fps" (EYKO-48) and a blur cut-off relative to each video (EYKO-74, 77).'],
  ['**Cards**', 'EYKO-4 (split), EYKO-5 (cheap filters), EYKO-6 (repeats), EYKO-45 (keyframe comparison), EYKO-59 (delete dropped pictures), EYKO-130 (still-video test), EYKO-131 (Katna), EYKO-132 (recent frames or whole video), EYKO-73 (store what the filter measured), EYKO-162 (this document). Not done: EYKO-48, 49, 74, 77, 79, 110, 46.'],
], { firstColFill: true }));

body.push(LABEL('How to use this document', { before: 240 }));
body.push(grid([2400, W - 2400], null, [
  ['**Part A · The card**', '2-minute refresh. Read this the night before.'],
  ['**Part B · The story**', 'How the work went, step by step. Use it to explain the Head out loud.'],
  ['**Part C · Hard questions**', 'What a strict examiner will ask, what to say, and what to show.'],
  ['**Part D · Evidence**', 'The tables to put in front of the professor. Every claim in A–C points here (E1, E2 …).'],
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
    P('The phone pulls **3 frames a second**, keeps only the **sharpest usable frame of each 3-second slot**, and drops repeats with a picture hash and then MobileCLIP. A 5-minute still video goes from **945 frames to 7**. Against five existing methods at the same number of frames, ours is **cheaper than evenly spaced frames, with close recall, not better**: it loses on short hand-held clips (31 against 34 of 35) and wins on long still clips (10 against 6 of 13), where it still misses small changes on an unchanged desk.', { run: { size: 23 }, after: 0, line: 300 }),
  ], W, { fill: C.accentSoft, pad: 160, borders: { top: NB, bottom: NB, right: NB, left: { style: BorderStyle.SINGLE, size: 24, color: C.accent } } })] })],
}));

body.push(LABEL('Where it sits in the pipeline'));
const stages = ['Pick + read', 'Split frames + sound', 'Filter + slot', 'Drop repeats', 'Scene models', 'Search'];
const sw = Math.floor(W / stages.length);
const swArr = stages.map((_, i) => (i === stages.length - 1 ? W - sw * (stages.length - 1) : sw));
body.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: swArr, layout: TableLayoutType.FIXED,
  rows: [
    new TableRow({ children: stages.map((s, i) => cell([new TextRun({ text: (i ? '→ ' : '') + s, size: 17, bold: true })], swArr[i], { align: AlignmentType.CENTER, valign: VerticalAlign.CENTER, fill: i >= 1 && i <= 3 ? C.accentSoft : undefined })) }),
    new TableRow({ children: [cell([new TextRun({ text: 'HEAD 4 · send the expensive models as few frames as possible without losing moments', bold: true, size: 18, color: 'FFFFFF' })], W, { span: stages.length, fill: C.accent, align: AlignmentType.CENTER, borders: { top: NB, bottom: NB, left: NB, right: NB } })] }),
  ],
}));
body.push(P('It comes after intake (Head 3) and before the scene models (Head 5). Every kept frame costs about 0.5 s of scene models, and about 2.3 s more where YOLOE runs, so each frame dropped here is time saved later.', { run: { size: 19, color: C.muted }, before: 80 }));

body.push(LABEL('What · Why · Result'));
const t3 = Math.floor(W / 3);
body.push(new Table({
  width: { size: W, type: WidthType.DXA }, columnWidths: [t3, t3, W - 2 * t3], layout: TableLayoutType.FIXED,
  rows: [
    new TableRow({ children: ['What we did', 'Why', 'Result'].map((h, i) => cell(h, i < 2 ? t3 : W - 2 * t3, { fill: C.head, bold: true, size: 18 })) }),
    new TableRow({ children: [
      cell('Built three stages on the phone (split, filter with a 3-second slot rule, drop repeats). Compared them with five existing methods at the same frame count, on our clips, on long still clips and on EPIC-KITCHENS. Tested one change (compare repeats with recent frames only) against a rule set before the run.', t3),
      cell('The scene models are the expensive part. The panel asked whether our selection beats existing keyframe methods on a phone, with numbers.', t3),
      cell('These stages fell from **137.5 to 32.6 s** per minute of video. Ours beats every method at equal count on long still clips (**10 of 13**; evenly spaced 6, Katna 7) but loses to evenly spaced frames on short clips (31 against 34 of 35). The recent-frames change failed its rule.', W - 2 * t3),
    ] }),
  ],
}));

body.push(LABEL('Numbers to remember'));
const nums = [
  ['945 → 7', 'frames of a 5-minute still classroom clip that reach the scene models (Pixel)', 'E5, E6'],
  ['10 vs 6', 'events found of 13 on long still clips: ours against evenly spaced, same 59 frames', 'E5'],
  ['31 vs 34', 'moments of 35 on short hand-held clips: ours loses to evenly spaced at 44 frames', 'E3'],
  ['23.6 s', 'of phone work per video minute for split + filter + repeats on 1080p camera video', 'E9'],
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
  ['3 frames a second at 640 px, decoded in one pass (EYKO-4).', 'Enough detail for the detectors. One pass with bulk pixel copies made splitting about 3× faster with identical JPEGs.', 'E9'],
  ['Plain-maths filters before any model (EYKO-5).', 'Dark, bright, blurry and unchanged frames cost about 0.7 s per video minute to drop.', 'E9'],
  ['Keep only the sharpest usable frame of each 3-second slot (13 Oct).', 'Checking every frame kept 227 of 416. The slot rule cut the cost from 137.5 to 32.6 s per minute, at 3 of 35 moments.', 'E3'],
  ['Drop repeats with a picture hash, then MobileCLIP cosine ≥ 0.95, against the whole video (EYKO-6).', 'The hash is nearly free and the vector is reused for search. Comparing with recent frames only failed its rule (EYKO-132).', 'E7, E10'],
  ['Do not claim our selection is better than evenly spaced frames.', 'It is not, on short clips; it wins only on long still video, and fails our own rule there.', 'E1, E3, E5'],
  ['Store each frame\'s brightness and sharpness (EYKO-73).', 'So every keep or drop can be shown afterwards, and a per-video cut-off can be built on it.', 'E6'],
]));

body.push(LABEL('Weak spots: say these before they find them'));
const weak = [
  ['Partly', 'On long still video ours misses small changes on an unchanged desk (3 of 8 events on S3-01): they are dropped as repeats of a frame from minutes earlier.'],
  ['Open', 'The supervisor\'s "check every 30 fps frame, keep the sharpest of each 1/3 s" (EYKO-48) is not built.'],
  ['Open', '"Dynamic blur" was never defined (EYKO-74), so the relative blur cut-off (EYKO-77) is not built. The numbers it needs are now stored.'],
  ['Partly', 'Small data: 35, 13 and 158 moments. On the 13-event set one event is 8 points.'],
  ['Partly', 'The cut-offs (25, 235, 60, 6 / 0.10, hash 6, cosine 0.95) are starting values. Tuning in October found no setting that beat evenly spaced frames.'],
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
  ['Question', null, 'Does our layered selection beat existing keyframe methods on a phone?', 'The panel asked this on 12 Oct, with numbers, and asked us to tune ours to match or beat them. Our method: 3 frames a second, cheap filters, then drop repeats.', null],
  ['Rule set before testing · 12 Oct', null, 'One protocol, equal budget', 'Five methods fixed in advance (evenly spaced, codec keyframes, ffmpeg scene filter, PySceneDetect, Katna). Every method keeps the same number of frames per clip as ours. Moment recall is the main measure; a frame counts only if it is sharp.', null],
  ['Test · 12 Oct · EYKO-45', 'bad', 'Every method found almost every moment, ours cost ten times more', 'On six short clips at 227 frames all methods hit 33 to 35 of 35. Ours spent almost all its time in the image model.', 'E1'],
  ['Tuning · 12 Oct', 'bad', 'No setting beat evenly spaced frames', 'A laptop copy tried 350 threshold settings on the tuning clips. Evenly spaced was ahead at every budget (50 frames: ours 23 of 26, evenly spaced 25).', 'E2'],
  ['Improvement · 13 Oct', 'ok', 'The slot rule cut the cost four times', 'Keeping only the sharpest frame of each 3-second slot took the phone from 137.5 to 32.6 s per video minute and from 227 to 44 frames, at the price of 3 moments (31 of 35; evenly spaced 34).', 'E3'],
  ['Outside data · 13 Oct', null, 'On EPIC-KITCHENS ours and evenly spaced are level', 'Eight head-camera kitchen videos, 158 moments marked by the dataset: ours 151, evenly spaced 153 (laptop copy, before the slot rule).', 'E4'],
  ['Test · 26 Nov · EYKO-130', 'bad', 'Long still video: best of all methods, but failed our rule', 'Two 5-minute camera clips with 13 events logged by a person. At 59 frames ours found 10, evenly spaced 6, PySceneDetect 7, ffmpeg 5. The rule set before the run asked for all 13 at half the frames evenly spaced needs: failed.', 'E5'],
  ['Finding · 27 Nov · EYKO-73', 'ok', 'The missed events were dropped as repeats of an old frame', 'Every frame now stores its brightness and sharpness. The S3-01 frame report shows the laptop being opened (122.3 s) dropped as a repeat of frame 7 (2.0 s), and the bottle (176.7 and 181.0 s) as a repeat of frame 430 (143 s).', 'E6'],
  ['Test · 27 Nov · EYKO-132', 'bad', 'Comparing with recent frames only failed its rule', 'W = 30 s fixed before the run: 10 of 13 events with 66 frames (rule: at least 12 with at most 59); EPIC unchanged at 79.1 %. Shorter windows win events back only by keeping more frames. The app keeps the whole-video rule.', 'E7'],
  ['Test · 27 Nov · EYKO-131', 'ok', 'Katna, the closest existing tool, finds the fewest moments', 'At our frame count: 27 of 35 short-clip moments (ours 31), 7 of 13 events (ours 10), 84 of 158 on EPIC (ours 125).', 'E8'],
  ['Still open', null, 'What comes next', 'The supervisor\'s 30 fps sharpest-per-1/3 s (EYKO-48). What "dynamic blur" means (EYKO-74) and a blur cut-off relative to each video (EYKO-77). The in-app frame list (EYKO-49). Dedup cut-off tuning (EYKO-79). Pixel against Infinix frame by frame (EYKO-110).', null],
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
  ['A1', 'A', 'Is your frame selection better than existing keyframe methods, on a phone?', 'Partly',
    'Not in general, and we do not claim it. At the same number of frames: on six short hand-held clips evenly spaced frames find **34 of 35** moments and ours **31**. On two long, mostly still clips ours finds **10 of 13** events, evenly spaced 6, PySceneDetect 7, Katna 7, ffmpeg 5. Our real gain is cost: these stages went from 137.5 to 32.6 s per video minute.',
    'E8 and Figure 1, E1, E3, E5 · `docs/results/2026-11-26-keyframes-still-video.md` · `docs/results/2026-11-27-keyframes-katna.md`',
    'On the long clips ours still failed the rule we wrote before the run (all 13 events, at half the frames evenly spaced needs). 13 events is a small set: one event is 8 points. EPIC ran on a laptop copy, not the phone.', 'Done: EYKO-45, 130, 131'],
  ['A2', 'A', 'Did you compare with Katna, the tool closest to your idea?', 'Answered',
    'Yes, at the same frame count on all three sets. Katna finds the fewest moments every time: **27 of 35** (ours 31, evenly spaced 34), **7 of 13** (ours 10) and **84 of 158** on EPIC (ours 125, evenly spaced 113). Katna 0.9.2, MIT, run untuned in its own environment.',
    'E8 · `docs/results/2026-11-27-keyframes-katna.md` · `src/benchmarks/keyframe_katna.py`',
    'Katna was built for edited video, ours is first-person video, which explains part of the gap. It is Python with OpenCV and scikit-learn and has no phone form. One timing was unusable (a 9 s clip took hours).', 'Done: EYKO-131'],
  ['A3', 'A', 'On a still video, do you drop the idle part and keep the short event?', 'Partly',
    'The idle part, yes: a 5-minute classroom clip went from **945 frames to 7**. The short events, not all: **5 of 8** on that clip. On a hand-held 5-minute clip it kept all 5 events but **52 frames**, where 19 evenly spaced frames would also catch all 5.',
    'E5, E6 · `docs/results/2026-11-26-keyframes-still-video.md`',
    'The missed events are small objects added to an unchanged desk (phone, laptop, bottle). Two clips, one person logging the times, one phone. Nothing was tuned on these clips.', 'Done: EYKO-130'],
  ['B1', 'B', 'Of the frames you stored, from which seconds, and why were the others dropped?', 'Answered',
    'Every frame is in the database with its second, kept or dropped, the reason, and since 27 Nov the **brightness and sharpness** the filter measured. The S3-01 frame report shows all 945 seconds: 840 "less sharp in their 3 s slot", 84 "still", 14 "duplicate of frame N", 7 kept. Each kept frame shows what each model said about it.',
    'E6 · `task frame-report -- pull 54cedacf` then `build 54cedacf` (page on the laptop: `D:/eykon-cache/frame-report/s3-01-2026-11-27.html`)',
    'The page is on the laptop, not in the app: the in-app frame list is EYKO-49. Dropped pictures are deleted when a video finishes, so their tiles show the numbers without a picture. The page shows classmates, so it stays off git.', 'Done: EYKO-73 · in-app: EYKO-49'],
  ['B2', 'B', 'Why did you miss those events?', 'Answered',
    'They were dropped as **repeats of a frame from minutes earlier**. The laptop being opened (122.3 s) was dropped as a repeat of frame 7 (2.0 s); the bottle (176.7 and 181.0 s) as a repeat of frame 430 (143 s). The desk looks the same to the picture hash and to MobileCLIP when only a small object changes. The filter did not cause it: those frames were sharp (sharpness about 970 to 1,080 against a cut-off of 60).',
    'E6 · frame report S3-01 · `docs/results/2026-11-27-dedup-recent-or-whole.md`',
    'This is the whole-video rule of the repeat layer: a frame is compared with every frame kept so far, so coming back to the same view is dropped too.', 'Done: EYKO-73, 132'],
  ['B3', 'B', 'Then why not compare only with recent frames?', 'Answered',
    'We tested it with a rule fixed before the run: adopt it at W = 30 s only if it finds at least 12 of 13 events with at most 59 frames and EPIC recall stays within 1 point. It found **10 with 66 frames**: failed. Shorter windows bring events back (5 s: 12 of 13) but only by keeping more frames (84), about what evenly spaced sampling needs. So the app keeps the whole-video rule.',
    'E7 · `docs/results/2026-11-27-dedup-recent-or-whole.md` · `src/benchmarks/keyframe_window.py`',
    'Run on a laptop copy of the phone\'s layers: it keeps 49 of the Pixel\'s 52 frames on the hand-held clip but only 3 of 7 on the still one, so rules were compared within the copy only. On EPIC the window changed nothing (79.1 % both).', 'Done: EYKO-132'],
  ['C1', 'C', 'The supervisor asked for "30 fps, filter, 3 fps": score every decoded frame, keep the sharpest of each 1/3 s. Did you?', 'Open',
    'Not built. Today the decoder keeps 3 frames a second and the filter picks the sharpest of each 3-second slot. Decoding is the largest cost left (about 12 to 13 s of the 23.6 s per video minute on the Pixel), which is what this would change.',
    'E9 · `docs/results/2026-11-26-keyframes-still-video.md` (phone cost)',
    'It needs the decoder to score every frame from its grey plane before any JPEG is written: a decoder rewrite, laptop benchmark first. It targets cost, not missed events (B2).', 'EYKO-48'],
  ['C2', 'C', 'What is "dynamic blur", and is your blur cut-off relative to the video?', 'Open',
    'Not decided and not built. The cut-off is a fixed 60 (variance of the Laplacian). Sharpness averages per video ran from 143 to 2,605 in October; on S3-01 every frame was between 377 and 1,167, so a fixed cut-off of 60 dropped nothing as blurry. The numbers a relative cut-off needs are now stored for every frame (EYKO-73).',
    'E6 · `frames.sharpness` in the phone database',
    'Two readings are possible: a cut-off relative to the video, or a Gaussian blur before the Laplacian. Neither is measured.', 'EYKO-74, 77'],
  ['C3', 'C', 'Are the cut-offs tuned?', 'Partly',
    'They are starting values: dark 25, bright 235, blur 60, still 6 and 0.10, hash 6 bits, cosine 0.95. In October a laptop copy tried 350 settings and none beat evenly spaced frames. Since then we only tested one rule change, with a rule set first, and it failed.',
    'E2, E7',
    'Dedup cut-off tuning is postponed (EYKO-79). Any new tuning must use clips we do not then report on.', 'EYKO-79 (postponed)'],
  ['D1', 'D', 'What does it cost on the phone?', 'Answered',
    'On the Pixel, 1080p camera video: **23.6 and 25.3 s of work per video minute** for split, filter and repeats (median of 3 runs). Splitting is most of it: frames about 12 to 13 s, the sound track about 9 s per minute. The filter is 0.7 s; repeats 0.8 s on the still clip and 7.7 s on the hand-held one (MobileCLIP about 520 ms per frame). Memory 199 MB.',
    'E9 · `docs/results/keyframes/pixel9proxl-still-2026-11-26.json`',
    'The phone was on the charger: no battery figure. On the short October clips the same stages were 32.6 s per minute (smaller files, more frames kept).', 'Done: EYKO-130'],
  ['D2', 'D', 'Does the phone choose the same frames as the laptop, and as other phones?', 'Partly',
    'Phone and laptop MobileCLIP vectors agree to cosine 0.997. On Head 3\'s kit clips the Pixel, Infinix and A32 keep the same number of frames (10 and 16). The laptop copy keeps 49 of the Pixel\'s 52 frames on S3-04 but 3 of 7 on S3-01, where a small decoding difference changes which frame of a slot is sharpest.',
    'E10 · Head 3 E1 · `docs/results/2026-11-27-dedup-recent-or-whole.md`',
    'A frame-by-frame Pixel against Infinix comparison was not done.', 'EYKO-110'],
];

body.push(LABEL('All questions at a glance', { before: 0 }));
body.push(grid([700, W - 700 - 1300 - 2000, 1300, 2000], ['#', 'Question', 'Status', 'Closes with'],
  Q.map((q) => [q[0], q[2], [chip(q[3])], q[7]])));
body.push(P('Groups: A = is the selection any good · B = which seconds, and why events were missed · C = the supervisor\'s requests and the cut-offs · D = cost and parity.', { run: { size: 17, color: C.muted }, before: 80 }));

const GROUPS = { A: 'A · Is the selection any good?', B: 'B · Which seconds, and why events were missed', C: 'C · The supervisor\'s requests and the cut-offs', D: 'D · Cost and parity' };
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
body.push(P('Open this part when the professor asks "show me". Each item says in one line what it proves, then the table, then the file it came from. "Moments hit" counts a moment when a kept frame inside it (±1 s) is sharp.', { run: { color: C.muted } }));

function ev(id, title, shows) {
  body.push(H2(`${id} · ${title}`));
  body.push(P([new TextRun({ text: 'What it shows: ', bold: true, size: 20 }), ...runs(shows, { size: 20 })], { after: 100, keepNext: true }));
}

ev('E1', 'First comparison on six short clips (12 Oct, before tuning)', 'At this budget every method finds almost every moment, so the test cannot separate them; ours cost about ten times more than evenly spaced frames on the phone.');
body.push(grid([3638, 2000, 2000, 2000], ['Method', 'Frames kept', 'Moments hit (35)', 'Kept outside every moment'], [
  ['Ours (phone)', '227', '34', '22 %'],
  ['B0 evenly spaced, same count', '227', '35', '23 %'],
  ['B1 codec keyframes', '142', '35', '23 %'],
  ['B2 ffmpeg scene filter', '227', '33', '32 %'],
  ['B3 PySceneDetect content', '138', '35', '25 %'],
], { firstColBold: true }));
body.push(SRC('docs/results/2026-10-12-keyframes-first-run.md · docs/results/keyframes/pixel9proxl-2026-10-12.json · moments: docs/results/keyframes/moments-2026-10-12-reviewed.csv'));

ev('E2', 'Tuning on the tuning clips (12 Oct)', 'A laptop copy of the phone\'s layers ran 350 threshold settings; evenly spaced frames were ahead of ours at every budget tried.');
body.push(P('Example at 50 frames: ours 23 of 26 tuning-clip moments, evenly spaced 25. Comparing repeats only with frames from the last 3 to 8 s was level with evenly spaced frames, within one moment. The held-out clips were not opened.', { run: { size: 20 } }));
body.push(SRC('docs/results/2026-10-12-keyframes-tuning.md · src/benchmarks/keyframe_tune.py'));

ev('E3', 'The 3-second slot rule on the phone (13 Oct)', 'Keeping only the sharpest frame of each 3-second slot cut the cost four times, at the price of 3 of 35 moments.');
body.push(grid([2638, 1400, 1100, 1700, 1400, 1400], ['', 'Pull frames', 'Filter', 'Repeats (MobileCLIP)', 'Total s / min', 'Kept of 416'], [
  ['Before (every frame)', '21.3', '1.4', '114.7', '137.5', '227'],
  ['Now (sharpest per 3 s)', '19.1', '1.0', '12.4', '**32.6**', '44'],
], { firstColBold: true, highlight: (r) => r[0].startsWith('Now') }));
body.push(P('Moments at 44 frames: **ours 31 of 35**, evenly spaced **34**, PySceneDetect content 29, adaptive 20, ffmpeg 13.', { run: { size: 20 }, before: 100 }));
body.push(SRC('docs/results/2026-10-13-keyframes-slots-on-phone.md · docs/results/keyframes/pixel9proxl-slots-2026-10-13.json'));

ev('E4', 'Outside data: EPIC-KITCHENS-100 (13 Oct, untuned)', 'On other people\'s marks, ours and evenly spaced frames are level (laptop copy, before the slot rule).');
body.push(grid([3638, 2000, 4000], ['Method', 'Frames', 'Moments hit (158)'], [
  ['Ours (laptop copy)', '900', '151 (96 %)'],
  ['B0 evenly spaced, same count', '900', '153 (97 %)'],
  ['B0 evenly spaced, 1 a second', '663', '154 (97 %)'],
  ['B3 PySceneDetect content', '592', '131 (83 %)'],
  ['B2 ffmpeg scene filter', '900', '127 (80 %)'],
  ['B1 codec keyframes', '110', '55 (35 %)'],
], { firstColBold: true }));
body.push(SRC('docs/results/2026-10-13-keyframes-epic-kitchens.md · src/benchmarks/keyframe_public.py'));

ev('E5', 'Long, mostly still clips on the Pixel (26 Nov, EYKO-130, untuned)', 'At the same 59 frames ours finds the most events of every method, but it fails the rule written before the run.');
body.push(grid([3638, 1400, 1700, 2900], ['Method', 'Frames kept', 'Events hit (13)', 'Kept in idle time'], [
  ['**Ours (Pixel)**', '59', '**10**', '41 of 59 (69 %)'],
  ['B0 evenly spaced, same count', '59', '6', '51 of 59 (86 %)'],
  ['B0 evenly spaced, 1 per 3 s', '201', '13', '163 of 201 (81 %)'],
  ['B1 codec keyframes', '604', '13', '491 of 604 (81 %)'],
  ['B2 ffmpeg scene filter', '59', '5', '39 of 59 (66 %)'],
  ['B3 PySceneDetect content', '59', '7', '44 of 59 (75 %)'],
  ['B4 Katna (27 Nov)', '59', '7', '43 of 59'],
], { firstColBold: true, highlight: (r) => r[0].startsWith('**Ours') }));
body.push(grid([3238, 2200, 2000, 2200], ['Clip', 'Ours: events / frames', 'Evenly spaced at our count', 'Fewest evenly spaced frames for all events'], [
  ['S3-01 classroom, 5:15 (8 events)', '5 / 7', '1', '30'],
  ['S3-04 outside, hand-held, 4:48 (5 events)', '5 / 52', '5', '19'],
], { firstColBold: true }));
body.push(P('**Rule written before the run:** every event, with at most half the frames evenly spaced sampling needs. S3-01 fails on events, S3-04 on frames. Events were logged by a person on 14 Oct; each became the window [t − 2, t + 5] s.', { run: { size: 20 }, before: 100 }));
body.push(SRC('docs/results/2026-11-26-keyframes-still-video.md · docs/results/keyframes/pixel9proxl-still-2026-11-26.json · score-still-2026-11-26.md · moments-still-2026-11-26.csv'));

ev('E6', 'Which seconds were kept, and why the rest were dropped: S3-01 in the app (27 Nov)', 'All 945 frames are accounted for. The three missed events were dropped as repeats of a frame from minutes earlier, not as blurry.');
body.push(grid([2000, 3000, 2638, 2000], ['Reason', 'Frames', 'What it means', 'Sharpness'], [
  ['less sharp', '840', 'not the sharpest of its 3 s slot', '377–1,167 (all frames)'],
  ['still', '84', 'the slot\'s best frame showed no change', ''],
  ['duplicate of frame N', '14', 'hash or MobileCLIP matched a kept frame', '896–1,084'],
  ['kept', '**7**', 'at 2.0, 129.7, 132.0, 143.0, 238.3, 296.7, 309.3 s', '942–1,167'],
], { firstColBold: true }));
body.push(grid([2400, 2400, 2438, 2400], ['Logged event', 'Window (s)', 'Best frame in the window', 'Dropped as'], [
  ['Phone put on the desk, 0:59', '57–64 (±1)', 'none kept; 66.7 s just after', 'duplicate of frame 7 (2.0 s)'],
  ['Laptop opened, 2:03', '121–128 (±1)', '122.3 s (frame 368)', '**duplicate of frame 7 (2.0 s)**'],
  ['Bottle placed, 2:58', '176–183 (±1)', '176.7 s and 181.0 s', '**duplicate of frame 430 (143.0 s)**'],
], { firstColBold: true }));
body.push(P('The same video in the app: 945 frames, 21 after the filter, 7 after repeats, as in the benchmark (E5). Brightness of the kept and duplicate frames 106–123. Brightness and sharpness are stored per frame since EYKO-73 and checked on the Pixel against the picture (`VideoFilterTest`, 14 of 14 with `VideoDedupTest`).', { run: { size: 20 }, before: 100 }));
body.push(SRC('frames table of the Pixel database, video 54cedacf · src/benchmarks/frame_report.py · page D:/eykon-cache/frame-report/s3-01-2026-11-27.html (not in git: shows classmates)'));

ev('E7', 'Repeats against the whole video or only the last W seconds (27 Nov, EYKO-132)', 'At W = 30 s, fixed before the run, recent-frames-only fails: 10 of 13 events with 66 frames. Shorter windows win events back only by keeping more frames.');
body.push(grid([3238, 1600, 1600, 1600, 1600], ['Rule (laptop copy)', 'Long clips: frames', 'Long clips: events (13)', 'EPIC: frames', 'EPIC: moments (158)'], [
  ['Whole video (the app today)', '58', '9', '175', '125 (79.1 %)'],
  ['Last 5 s only', '84', '12', '180', '126 (79.7 %)'],
  ['Last 10 s only', '76', '11', '177', '125 (79.1 %)'],
  ['**Last 30 s only (the decision)**', '**66**', '**10**', '175', '125 (79.1 %)'],
  ['Last 60 s only', '63', '10', '175', '125 (79.1 %)'],
], { firstColBold: true, highlight: (r) => r[0].includes('decision') }));
body.push(P('**Rule:** adopt only if at least 12 of 13 events with at most 59 frames, and EPIC within 1 point. **How close the copy is to the phone:** S3-01 3 of the Pixel\'s 7 frames at the same second, S3-04 49 of 52; the copy finds 9 events where the Pixel finds 10, so rules are compared within the copy only.', { run: { size: 20 }, before: 100 }));
body.push(SRC('docs/results/2026-11-27-dedup-recent-or-whole.md · docs/results/keyframes/window-still-2026-11-27.md · window-epic-2026-11-27.md · src/benchmarks/keyframe_window.py'));

ev('E8', 'Katna and every method side by side, at our frame count (27 Nov, EYKO-131)', 'Katna finds the fewest moments of all methods on every set; ours leads on the long still clips and EPIC, and trails evenly spaced frames on the short clips.');
body.push(grid([3638, 1200, 1200, 1800, 1800], ['Data', 'Frames', 'Ours', 'Evenly spaced', '**Katna**'], [
  ['Six short own clips (35 moments)', '44', '31', '34', '**27**'],
  ['S3-01 + S3-04 (13 events)', '59', '10', '6', '**7**'],
  ['EPIC-KITCHENS-100 (158 moments; ours = laptop copy)', '175', '125', '113', '**84**'],
], { firstColBold: true }));
figure('head4-methods.png', '**Figure 1.** Share of marked moments found by every method at the same frame count as ours, on the three data sets. Ours is best on the long still clips and on EPIC, and behind evenly spaced frames on the short clips. PySceneDetect and ffmpeg were not run at the EPIC budget. Drawn by `figures/head4_keyframes.py` from the saved result tables.');
body.push(P('Katna 0.9.2 (MIT), one-off environment, asked for exactly our frame count. Its pictures were matched back to the decoded frame they came from to get their times. Long clips were given to it as 360 p copies. Laptop cost 7.5 to 10.8 s per video minute; one 9 s clip took hours and is left out.', { run: { size: 20 }, before: 100 }));
body.push(SRC('docs/results/2026-11-27-keyframes-katna.md · docs/results/keyframes/katna-six-clips-2026-11-27.md · katna-still-2026-11-27.md · katna-epic-2026-11-27.md · src/benchmarks/keyframe_katna.py'));

ev('E9', 'Phone cost per stage on 1080p camera video (26 Nov)', 'Splitting is most of the cost. MobileCLIP only matters when many frames survive the filter.');
body.push(grid([2438, 2600, 1000, 1800, 1800], ['Clip (Pixel, median of 3)', 'Split (frames + sound)', 'Filter', 'Repeats', 'Seconds per video minute'], [
  ['S3-01, 5:15', '115.9 s (frames 62–69, sound 47–50)', '3.4 s', '4.3 s (8 pictures)', '**23.6**'],
  ['S3-04, 4:48', '81.0 s (frames 40–47, sound 27–41)', '3.7 s', '37.0 s (70 pictures)', '**25.3**'],
], { firstColBold: true }));
body.push(P('Native memory 199 MB on every run. Splitting got about 3× faster on 15 Nov with identical JPEGs (one decoder pass, bulk pixel copies; Head 3 E11). The phone was on the charger, so there is no battery figure.', { run: { size: 20 }, before: 100 }));
body.push(SRC('docs/results/keyframes/pixel9proxl-still-2026-11-26.json · pixel-still-2026-11-26-eykonvideo.log · docs/results/2026-11-17-split-frames-faster.md'));

ev('E10', 'Phone and laptop see the same thing (dedup parity)', 'MobileCLIP vectors on the phone and the laptop agree, so the laptop can stand in for the phone in comparisons of the model.');
body.push(P('Cosine between phone and laptop vectors of the same pictures: **0.997** (0.9968 to 0.9998 in the 27 Nov on-device run). About 544 ms per picture for the image encoder on the Pixel (median 543, worst 594 over 10 runs).', { run: { size: 20 } }));
body.push(SRC('android/app/src/androidTest/.../VideoDedupTest.kt (real-model tests) · logcat EykonVideo "clip parity", 27 Nov'));

body.push(H2('Limits: how these numbers could mislead'));
[
  'Small sets: 35, 13 and 158 moments. On the 13-event set one event is 8 points, so "10 against 6" is a direction, not a proof.',
  '16 of the 35 October moments were marked by the AI assistant; the person checked 19. The 13 long-clip events were logged by a person before any run.',
  'EPIC and the recent-frames test ran on a laptop copy of the phone\'s layers, not on the phone. The copy matches the phone closely on hand-held video and loosely on still video.',
  'Our own clips: our rooms, our classmates, one phone per run, mostly on the charger.',
  'Katna and PySceneDetect ran on 360 p copies of the long clips; scoring used the originals.',
].forEach((t) => body.push(bullet(t)));

// ======================================================================
// PART E
// ======================================================================
body.push(BREAK());
body.push(H1('Part E · Words, gaps, upkeep'));
body.push(H2('Words in plain language'));
body.push(grid([2338, W - 2338], ['Word', 'What it means here'], [
  ['Keyframe', 'A frame we keep and send on to the scene models.'],
  ['Split', 'Decoding the video into 3 frames a second (640 px JPEGs) and the sound track (16 kHz WAV).'],
  ['Slot rule', 'Frames are grouped into 3-second slots; only the sharpest usable frame of each slot can be kept.'],
  ['Sharpness', 'Variance of the Laplacian on a small grey copy: high when edges are crisp, low when blurry.'],
  ['Still', 'The slot\'s best frame barely differs from the last kept frame (pixel change < 6 and histogram change < 0.10).'],
  ['dHash', 'A 64-bit picture fingerprint; two frames at most 6 bits apart look the same.'],
  ['MobileCLIP', 'The image model that turns a frame into a 512-number vector; cosine ≥ 0.95 means "shows the same thing".'],
  ['Whole video / last W seconds', 'Whether a new frame is compared with every frame kept so far, or only with frames kept in the last W seconds.'],
  ['Equal budget', 'Every method keeps the same number of frames per clip as ours, so recall is compared fairly.'],
  ['Moment recall', 'Share of marked moments with a sharp kept frame inside them (±1 s).'],
  ['Evenly spaced', 'The simplest method: N frames at equal intervals, no model.'],
  ['Katna, PySceneDetect, ffmpeg scene filter', 'Existing tools that pick keyframes from picture changes; Katna also clusters frames and keeps the sharpest per cluster.'],
  ['Laptop copy', 'A Python version of the phone\'s filter and repeat layers, used to try rules quickly.'],
], { firstColBold: true }));

body.push(H2('Open gaps for this Head'));
body.push(grid([800, 3938, 1600, 1100, 2200], ['Gap', 'What is missing', 'Card', 'Severity', 'Resolution'], [
  ['G1', 'Frame filter cut-offs never tuned; an adaptive blur cut-off.', 'EYKO-77', 'High', ''],
  ['D1', 'What "dynamic blur" means.', 'EYKO-74', 'Decision', ''],
  ['G7', 'Store what the filter measured per frame.', 'EYKO-73', 'Medium', 'Closed 27 Nov: `frames.brightness`, `frames.sharpness`, checked on the Pixel.'],
  ['G3', 'Dedup cut-offs untuned (hash 6, cosine 0.95).', 'EYKO-79', 'Medium', 'Postponed.'],
  ['—', 'Recent frames or whole video for repeats.', 'EYKO-132', 'Decision', 'Closed 27 Nov: whole video stays (W = 30 s failed its rule).'],
  ['—', 'Katna in the comparison.', 'EYKO-131', '—', 'Closed 27 Nov: fewest moments on every set.'],
  ['—', 'Still-video test.', 'EYKO-130', '—', 'Done 26 Nov: best at equal count, failed its rule.'],
  ['—', 'Score every 30 fps frame, keep the sharpest of each 1/3 s.', 'EYKO-48', '—', ''],
  ['—', 'In-app list of every frame\'s second, kept or dropped and why.', 'EYKO-49', '—', 'Laptop page exists (E6).'],
  ['—', 'Pixel against Infinix, frame by frame.', 'EYKO-110', '—', ''],
  ['—', 'Slot length and a precision measure.', 'EYKO-46', 'Low', 'Later.'],
]));

body.push(H2('How to update this document'));
[
  'When a card closes: change the question\'s status in Part C, rewrite "Say this" with the new numbers, add the new table to Part D as the next E number, and change the date on the cover.',
  'If the result changes a number in Part A, update Part A too. Part A must always match the latest evidence.',
  'Never delete an old finding. If a new run disagrees, say so in "Say this" and keep the old table in Part D.',
  'Add a step to Part B only for something that changed the direction of the work.',
].forEach((t) => body.push(bullet(t)));

body.push(H2('References'));
[
  'Code: `android/…/video/VideoSplit.kt`, `FrameExtractor.kt`, `FrameFilters.kt`, `VideoFilter.kt`, `FrameHash.kt`, `VideoDedup.kt`, `VideoSchema.kt`',
  'Protocol: `docs/plans/keyframe-comparison-protocol.md`',
  'Scripts: `src/benchmarks/keyframe_eval.py`, `keyframe_tune.py`, `keyframe_public.py`, `keyframe_window.py`, `keyframe_katna.py`, `frame_report.py`',
  'Phone benchmark: `android/app/src/androidTest/.../KeyframeBenchmarkTest.kt`',
  'Record document: `docs/documents/source/heads/head4.json`',
  'Graph: `docs/documents/source/figures/head4_keyframes.py` (run from the repo root with `uv run`)',
].forEach((t) => body.push(bullet(t)));

// ======================================================================
const doc = new Document({
  creator: 'Eykon', title: 'Head 4 · Video processing',
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
      new TextRun({ text: 'Eykon · Head 4 · Video processing  ·  page ', size: 16, color: C.muted }),
      new TextRun({ children: [PageNumber.CURRENT], size: 16, color: C.muted }),
    ] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = process.argv[2] || path.join(__dirname, '..', 'Head-4-Video-processing.docx');
  fs.writeFileSync(out, buf);
  console.log('wrote', out, buf.length);
});
