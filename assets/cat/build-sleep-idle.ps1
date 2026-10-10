Add-Type -AssemblyName System.Drawing
$sheet = [System.Drawing.Bitmap]::new((Join-Path $PSScriptRoot 'sleep-idle-sheet-v2.png'))
$baseFrame = $sheet.Clone([System.Drawing.Rectangle]::new(0,0,443,443), [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$sheet.Dispose()
# Remove stray generation pixels from the area reserved for fading letters.
for ($y=105; $y -lt 200; $y++) {
    for ($x=238; $x -lt 380; $x++) {
        $baseFrame.SetPixel($x,$y,[System.Drawing.Color]::Transparent)
    }
}
$outputDir = Join-Path $PSScriptRoot 'sleep-idle'
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
# Shared body registration; a 16-frame breath with a stronger belly rise.
$textSheet = [System.Drawing.Bitmap]::new((Join-Path $PSScriptRoot 'sleep-idle-sheet.png'))
$glyphs = @(
    [System.Drawing.Rectangle]::new(238,105,52,95),
    [System.Drawing.Rectangle]::new(290,105,47,95),
    [System.Drawing.Rectangle]::new(337,105,43,95)
)
for ($i=0; $i -lt 16; $i++) {
    $breath = 20*(1-[Math]::Cos(2*[Math]::PI*$i/15))/2
    $frame = [System.Drawing.Bitmap]::new(443,443,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $copyGraphics = [System.Drawing.Graphics]::FromImage($frame)
    $copyGraphics.DrawImageUnscaled($baseFrame,0,0)
    $copyGraphics.Dispose()
    if ($breath -gt 0.001) {
        for ($y=190; $y -lt 370; $y++) {
            for ($x=240; $x -lt 443; $x++) {
                $distance = [Math]::Pow(($x-335)/100.0,2)+[Math]::Pow(($y-270)/95.0,2)
                if ($distance -ge 1) { continue }
                $falloff = [Math]::Pow(1-$distance,2)
                $sampleY = $y+$breath*$falloff
                $low = [int][Math]::Floor($sampleY)
                $blend = $sampleY-$low
                $a = $baseFrame.GetPixel($x,$low)
                $b = $baseFrame.GetPixel($x,$low+1)
                $outA = [int][Math]::Round($a.A*(1-$blend)+$b.A*$blend)
                if ($outA -eq 0) {
                    $frame.SetPixel($x,$y,[System.Drawing.Color]::Transparent)
                    continue
                }
                $r = [int][Math]::Round(($a.R*$a.A*(1-$blend)+$b.R*$b.A*$blend)/$outA)
                $g = [int][Math]::Round(($a.G*$a.A*(1-$blend)+$b.G*$b.A*$blend)/$outA)
                $blue = [int][Math]::Round(($a.B*$a.A*(1-$blend)+$b.B*$b.A*$blend)/$outA)
                $r = [Math]::Min(255,$r)
                $g = [Math]::Min(255,$g)
                $blue = [Math]::Min(255,$blue)
                $frame.SetPixel($x,$y,[System.Drawing.Color]::FromArgb($outA,$r,$g,$blue))
            }
        }
    }
    $graphics = [System.Drawing.Graphics]::FromImage($frame)
    for ($letter=0; $letter -lt 3; $letter++) {
        $opacity = [Math]::Max(0.0,[Math]::Min(1.0,[Math]::Min(($i-(1+2*$letter))/3.0,(15-$i)/5.0)))
        if ($opacity -le 0) { continue }
        $matrix = [System.Drawing.Imaging.ColorMatrix]::new()
        $matrix.Matrix33 = [single]$opacity
        $attributes = [System.Drawing.Imaging.ImageAttributes]::new()
        $attributes.SetColorMatrix($matrix)
        $rect = $glyphs[$letter]
        $graphics.DrawImage($textSheet,$rect,$rect.X,$rect.Y,$rect.Width,$rect.Height,[System.Drawing.GraphicsUnit]::Pixel,$attributes)
        $attributes.Dispose()
    }
    $graphics.Dispose()
    $frame.Save((Join-Path $outputDir ('sleep_{0:000}.png' -f $i)),[System.Drawing.Imaging.ImageFormat]::Png)
    $frame.Dispose()
}
$baseFrame.Dispose()
$textSheet.Dispose()
Write-Output 'Saved 16 breathing frames with staggered Z Z z appearance and fade-out.'
