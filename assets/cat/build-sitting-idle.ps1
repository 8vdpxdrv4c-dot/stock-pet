Add-Type -AssemblyName System.Drawing
$source = [System.Drawing.Bitmap]::new((Join-Path $PSScriptRoot 'sitting-calm-base.png'))
$baseFrame = [System.Drawing.Bitmap]::new(443,443,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$graphics = [System.Drawing.Graphics]::FromImage($baseFrame)
$graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$graphics.DrawImage($source,[System.Drawing.Rectangle]::new(0,0,443,443))
$graphics.Dispose()
$source.Dispose()
$outputDir = Join-Path $PSScriptRoot 'sitting-idle'
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
for ($i=0; $i -lt 8; $i++) {
    $frame = $baseFrame.Clone([System.Drawing.Rectangle]::new(0,0,443,443),[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $swing = 12*[Math]::Sin(2*[Math]::PI*$i/7)
    if ([Math]::Abs($swing) -gt 0.001) {
        for ($y=260; $y -lt 410; $y++) {
            $boundary = 350+15*[Math]::Max(0.0,[Math]::Min(1.0,($y-315)/70.0))
            $vertical = [Math]::Pow((410-$y)/150.0,1.2)
            for ($x=[int][Math]::Ceiling($boundary); $x -lt 443; $x++) {
                $horizontal = [Math]::Min(1.0,($x-$boundary)/18.0)
                $sampleX = $x-$swing*$vertical*$horizontal
                $low = [int][Math]::Floor($sampleX)
                if ($low -lt 0 -or $low+1 -ge 443) {
                    $frame.SetPixel($x,$y,[System.Drawing.Color]::Transparent)
                    continue
                }
                $blend = $sampleX-$low
                $a = $baseFrame.GetPixel($low,$y)
                $b = $baseFrame.GetPixel($low+1,$y)
                $alpha = [int][Math]::Round($a.A*(1-$blend)+$b.A*$blend)
                if ($alpha -eq 0) {
                    $frame.SetPixel($x,$y,[System.Drawing.Color]::Transparent)
                    continue
                }
                $r = [int][Math]::Min(255.0,[Math]::Round(($a.R*$a.A*(1-$blend)+$b.R*$b.A*$blend)/$alpha))
                $g = [int][Math]::Min(255.0,[Math]::Round(($a.G*$a.A*(1-$blend)+$b.G*$b.A*$blend)/$alpha))
                $blue = [int][Math]::Min(255.0,[Math]::Round(($a.B*$a.A*(1-$blend)+$b.B*$b.A*$blend)/$alpha))
                $frame.SetPixel($x,$y,[System.Drawing.Color]::FromArgb($alpha,$r,$g,$blue))
            }
        }
    }
    $frame.Save((Join-Path $outputDir ('idle_{0:000}.png' -f $i)),[System.Drawing.Imaging.ImageFormat]::Png)
    $frame.Dispose()
}
$baseFrame.Dispose()
Write-Output 'Saved 8 quiet sitting frames; only the tail sways.'
