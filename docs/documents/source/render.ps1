# Saves a .docx as PDF through Word, to check the pages. Usage: .\render.ps1 -Docx <full path> -Pdf <full path>
param([string]$Docx, [string]$Pdf)
$w = New-Object -ComObject Word.Application
$w.Visible = $false
try {
  $d = $w.Documents.Open($Docx, $false, $true)
  $d.SaveAs([ref]$Pdf, [ref]17)
  $d.Close([ref]0)
} finally { $w.Quit() }
