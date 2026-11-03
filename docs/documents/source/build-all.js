// Rebuilds every head document into docs/documents/. Usage: npm run build (from this folder).
const { execFileSync } = require("child_process");
const path = require("path");

const NAMES = {
  1: "Project-start", 2: "Setup-and-storage-decisions", 3: "Video-intake", 4: "Video-processing",
  5: "Scene-understanding", 6: "Indexing-and-memory", 7: "Search", 8: "Evaluation",
};

for (const [n, name] of Object.entries(NAMES)) {
  const src = path.join(__dirname, "heads", `head${n}.json`);
  const out = path.join(__dirname, "..", `Head-${n}-${name}.docx`);
  execFileSync(process.execPath, [path.join(__dirname, "build.js"), src, out], { stdio: "inherit" });
}
