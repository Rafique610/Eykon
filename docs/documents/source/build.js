// Builds one Word document per head from heads/<name>.json.
// Usage: node build.js heads/head1.json ../Head-1-Project-start.docx (or npm run build for all eight)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  HeadingLevel, AlignmentType, BorderStyle, LevelFormat, Footer, Header, PageNumber, TabStopType,
} = require("docx");

const [, , src, out] = process.argv;
const d = JSON.parse(fs.readFileSync(src, "utf8"));

const FONT = "Calibri";
const ACCENT = "1F4E79";
const PAGE_W = 11906, MARGIN = 1134, TEXT_W = PAGE_W - 2 * MARGIN; // A4, 2 cm margins

// "**bold**" inside a string becomes bold runs.
function runs(text, opts = {}) {
  return String(text).split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((part) =>
    part.startsWith("**")
      ? new TextRun({ text: part.slice(2, -2), bold: true, font: FONT, ...opts })
      : new TextRun({ text: part, font: FONT, ...opts }));
}

const para = (text, opts = {}) => new Paragraph({ children: runs(text), spacing: { after: 120 }, ...opts });

const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };

function table(t) {
  const n = t.cols.length;
  const widths = (t.widths || Array(n).fill(1)).map(Number);
  const sum = widths.reduce((a, b) => a + b, 0);
  const dxa = widths.map((w) => Math.floor((w / sum) * TEXT_W));
  dxa[n - 1] += TEXT_W - dxa.reduce((a, b) => a + b, 0);
  const cell = (text, i, head) => new TableCell({
    borders,
    width: { size: dxa[i], type: WidthType.DXA },
    shading: head ? { fill: "DCE6F1", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: runs(text ?? "", head ? { size: 19, bold: true } : { size: 19 }) })],
  });
  return new Table({
    width: { size: TEXT_W, type: WidthType.DXA },
    columnWidths: dxa,
    rows: [
      new TableRow({ tableHeader: true, children: t.cols.map((c, i) => cell(c, i, true)) }),
      ...t.rows.map((r) => new TableRow({ children: r.map((c, i) => cell(c, i, false)) })),
    ],
  });
}

function note(text) {
  return new Paragraph({
    children: runs(text, { size: 20 }),
    shading: { fill: "F2F2F2", type: ShadingType.CLEAR, color: "auto" },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 8 } },
    spacing: { before: 120, after: 160 },
    indent: { left: 120 },
  });
}

function blocks(list) {
  const outEls = [];
  for (const b of list) {
    if (typeof b === "string") outEls.push(para(b));
    else if (b.h3) outEls.push(new Paragraph({ heading: HeadingLevel.HEADING_3, children: runs(b.h3) }));
    else if (b.bullets) b.bullets.forEach((x) => outEls.push(new Paragraph({ numbering: { reference: "bul", level: 0 }, children: runs(x), spacing: { after: 60 } })));
    else if (b.steps) b.steps.forEach((x) => outEls.push(new Paragraph({ numbering: { reference: b.ref || "num", level: 0 }, children: runs(x), spacing: { after: 60 } })));
    else if (b.table) { outEls.push(table(b.table)); outEls.push(new Paragraph({ spacing: { after: 120 }, children: [] })); }
    else if (b.note) outEls.push(note(b.note));
  }
  return outEls;
}

const body = [
  new Paragraph({ children: [new TextRun({ text: "EYKON · PIPELINE DOCUMENTATION", font: FONT, size: 20, color: "7F7F7F", bold: true })], spacing: { after: 80 } }),
  new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text: d.title, font: FONT })] }),
  new Paragraph({ children: runs(d.subtitle, { size: 24, color: "404040" }), spacing: { after: 240 } }),
  table({ cols: ["Item", "Detail"], widths: [1, 3], rows: d.meta }),
  new Paragraph({ spacing: { after: 120 }, children: [] }),
];
// Each section is one numbered heading followed by its blocks.
d.sections.forEach((s, i) => {
  body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: `${i + 1}. ${s.title}`, font: FONT })] }));
  body.push(...blocks(s.blocks));
});

// Numbered lists restart per section by giving each its own reference.
const numRefs = new Set(["num"]);
JSON.stringify(d).replace(/"ref":"([^"]+)"/g, (_, r) => numRefs.add(r));

const doc = new Document({
  creator: "Eykon project",
  title: d.title,
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", run: { size: 44, bold: true, color: ACCENT, font: FONT }, paragraph: { spacing: { after: 120 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 30, bold: true, color: ACCENT, font: FONT }, paragraph: { keepNext: true, spacing: { before: 360, after: 140 }, outlineLevel: 0, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 4 } } } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 24, bold: true, color: "2E75B6", font: FONT }, paragraph: { keepNext: true, spacing: { before: 200, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
      ...[...numRefs].map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 340 } } } }] })),
    ],
  },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: d.header, font: FONT, size: 16, color: "7F7F7F" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W }], children: [
      new TextRun({ text: `Eykon · ${d.date}`, font: FONT, size: 16, color: "7F7F7F" }),
      new TextRun({ children: ["\tPage ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], font: FONT, size: 16, color: "7F7F7F" }),
    ] })] }) },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log("wrote", out); });
