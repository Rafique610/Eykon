# Downloads the two source packages EYKO-108 builds and checks their SHA256 (the sources are not committed).
$dir = Join-Path $PSScriptRoot "third_party"
New-Item -ItemType Directory -Force $dir | Out-Null
$files = @(
  @{ Url = "https://sqlite.org/2026/sqlite-amalgamation-3530400.zip"; Sha = "1e71ddf93849c6a6ecf58b827c0692073d2dd7ee40196158068f7b29f422e87d" },
  @{ Url = "https://github.com/asg017/sqlite-vec/releases/download/v0.1.9/sqlite-vec-0.1.9-amalgamation.zip"; Sha = "b87cdda12112657ba5ab8842f0088a4090982eaf41f22b2bd6d495b81765a8c9" }
)
foreach ($f in $files) {
  $zip = Join-Path $dir (Split-Path $f.Url -Leaf)
  Invoke-WebRequest -Uri $f.Url -OutFile $zip -UseBasicParsing
  if ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLower() -ne $f.Sha) { throw "SHA256 mismatch: $zip" }
  Expand-Archive -Path $zip -DestinationPath $dir -Force
}
# sqlite3.c, sqlite3.h from sqlite-amalgamation-3530400/, sqlite-vec.c and .h from the second zip
Copy-Item (Join-Path $dir "sqlite-amalgamation-3530400\sqlite3*") $dir -Force
"done: SQLite 3.53.4 and sqlite-vec 0.1.9 are in $dir"
