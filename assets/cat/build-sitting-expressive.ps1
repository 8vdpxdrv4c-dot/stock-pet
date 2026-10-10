Add-Type -AssemblyName System.Drawing
$sheet = [System.Drawing.Bitmap]::new((Join-Path $PSScriptRoot 'sitting-reference-sheet.png'))
$baseFrame = $sheet.Clone([System.Drawing.Rectangle]::new(0,0,443,443), [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$outputDir = Join-Path $PSScriptRoot 'sitting-idle'
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
$keyframes = @()
$noseX = @(238,220,220,202,238,220,218,202)
$noseY = @(142,142,142,142,140,142,140,142)
for ($i=0; $i -lt 8; $i++) {
    $frame = [System.Drawing.Bitmap]::new(443,443,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($frame)
    $graphics.DrawImageUnscaled($baseFrame,0,0)
    $graphics.Dispose()
    if ($i -gt 0 -and $i -lt 7) {
        $col = $i%4
        $row = [int][Math]::Floor($i/4)
        $offsetX = [int][Math]::Round($col*$sheet.Width/4)+$noseX[$i]-238
        $offsetY = [int][Math]::Round($row*$sheet.Height/2)+$noseY[$i]-142
        for ($y=78; $y -le 214; $y++) {
            for ($x=138; $x -le 338; $x++) {
                $radius = [Math]::Sqrt([Math]::Pow(($x-238)/100.0,2)+[Math]::Pow(($y-146)/68.0,2))
                if ($radius -ge 1) { continue }
                $weight = [Math]::Min(1.0,(1-$radius)/0.2)
                $src = $sheet.GetPixel($x+$offsetX,$y+$offsetY)
                $dst = $baseFrame.GetPixel($x,$y)
                $r = [int][Math]::Round($dst.R*(1-$weight)+$src.R*$weight)
                $g = [int][Math]::Round($dst.G*(1-$weight)+$src.G*$weight)
                $b = [int][Math]::Round($dst.B*(1-$weight)+$src.B*$weight)
                $frame.SetPixel($x,$y,[System.Drawing.Color]::FromArgb($dst.A,$r,$g,$b))
            }
        }
    }
    $keyframes += $frame
}
# Six eased steps between each pair of expressions: 48 frames at 20 fps.
# Body and alpha silhouette stay identical; only registered face pixels blend.
for ($i=0; $i -lt 8; $i++) {
    $from = $keyframes[$i]
    $to = $keyframes[($i+1)%8]
    for ($step=0; $step -lt 6; $step++) {
        $t = $step/6.0
        $weight = $t*$t*(3-2*$t)
        $frame = [System.Drawing.Bitmap]::new(443,443,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $graphics = [System.Drawing.Graphics]::FromImage($frame)
        $graphics.DrawImageUnscaled($from,0,0)
        $graphics.Dispose()
        if ($step -gt 0 -and $i -lt 7) {
            for ($y=78; $y -le 214; $y++) {
                for ($x=138; $x -le 338; $x++) {
                    $a = $from.GetPixel($x,$y)
                    $b = $to.GetPixel($x,$y)
                    $r = [int][Math]::Round($a.R*(1-$weight)+$b.R*$weight)
                    $g = [int][Math]::Round($a.G*(1-$weight)+$b.G*$weight)
                    $blue = [int][Math]::Round($a.B*(1-$weight)+$b.B*$weight)
                    $frame.SetPixel($x,$y,[System.Drawing.Color]::FromArgb($a.A,$r,$g,$blue))
                }
            }
        }
        $index = $i*6+$step
        $frame.Save((Join-Path $outputDir ('idle_{0:000}.png' -f $index)),[System.Drawing.Imaging.ImageFormat]::Png)
        $frame.Dispose()
    }
}
foreach ($keyframe in $keyframes) { $keyframe.Dispose() }
$baseFrame.Dispose()
$sheet.Dispose()
Write-Output 'Saved 48 sitting frames with fixed short tail, neutral endpoints and eased smile/lick transitions.'
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'sitting-recovery-sheet.png')) {
    & (Join-Path $PSScriptRoot 'apply-sitting-recovery.ps1')
}
