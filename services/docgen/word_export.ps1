# SPIKE-01: Word oracle — docx -> pdf + page/line stats via COM (Word is the
# renderer the user actually downloads from, so it is the ground truth).
param(
  [Parameter(Mandatory=$true)][string]$Docx,
  [Parameter(Mandatory=$true)][string]$Pdf,
  [Parameter(Mandatory=$true)][string]$StatsJson
)
$ErrorActionPreference = "Stop"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($Docx, $false, $true)
  $pages = $doc.ComputeStatistics(2)    # wdStatisticPages
  $lines = $doc.ComputeStatistics(1)    # wdStatisticLines
  $words = $doc.ComputeStatistics(0)    # wdStatisticWords
  $doc.ExportAsFixedFormat($Pdf, 17)    # wdExportFormatPDF
  $doc.Close($false)
  $obj = [ordered]@{ pages = $pages; lines = $lines; words = $words }
  $obj | ConvertTo-Json | Set-Content -Path $StatsJson -Encoding UTF8
} finally {
  $word.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
