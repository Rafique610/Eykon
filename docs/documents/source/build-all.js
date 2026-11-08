// Rebuilds every head document into docs/documents/. Usage: npm run build (from this folder).
// Heads with a defense doc are built from head<N>-defense.js; the rest from heads/head<N>.json.
const { execFileSync } = require("child_process");
const path = require("path");

const RECORD = {
  1: "Project-start", 3: "Video-intake", 4: "Video-processing",
  5: "Scene-understanding", 6: "Indexing-and-memory", 7: "Search", 8: "Evaluation",
};
const DEFENSE = [2];

const run = (args) => execFileSync(process.execPath, args, { stdio: "inherit" });
for (const n of DEFENSE) run([path.join(__dirname, `head${n}-defense.js`)]);
for (const [n, name] of Object.entries(RECORD)) {
  run([path.join(__dirname, "build.js"), path.join(__dirname, "heads", `head${n}.json`), path.join(__dirname, "..", `Head-${n}-${name}.docx`)]);
}
