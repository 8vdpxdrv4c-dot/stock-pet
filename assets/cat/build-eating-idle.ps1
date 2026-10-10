Add-Type -AssemblyName System.Drawing
$assetRoot = $PSScriptRoot
$sheet = [System.Drawing.Bitmap]::new((Join-Path $assetRoot 'eating-two-bites-sheet.png'))
$baseFrame = [System.Drawing.Bitmap]::new((Join-Path $assetRoot 'eating-idle-chewing/idle_000.png'))
$headBottoms = @(270, 310, 350, 315, 350, 295)
$outputDir = Join-Path $assetRoot 'eating-idle'
# Four chewing frames, eight eating frames, then four chewing frames.
for ($i = 0; $i -lt 4; $i++) {
    Copy-Item -LiteralPath (Join-Path $assetRoot ('eating-idle-chewing/idle_{0:000}.png' -f $i)) -Destination (Join-Path $outputDir ('idle_{0:000}.png' -f $i))
}
for ($i = 0; $i -lt 8; $i++) {
    $frame = $baseFrame.Clone([System.Drawing.Rectangle]::new(0,0,443,443), [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    if ($i -lt 6) {
        $col = $i % 4
        $row = [int][Math]::Floor($i/4)
        $offsetX = [int][Math]::Round($col*$sheet.Width/4)
        $offsetY = [int][Math]::Round($row*$sheet.Height/2)
        $bottom = $headBottoms[$i]
        for ($y=0; $y -lt $bottom; $y++) {
            for ($x=0; $x -lt 443; $x++) {
                $src = $sheet.GetPixel($x+$offsetX,$y+$offsetY)
                # Above the neck, replace the upright head completely.
                if ($y -lt 235) {
                    $frame.SetPixel($x,$y,$src)
                    continue
                }
                # Feather the chin into the shared torso; bowl and paws stay exact.
                $weight = [Math]::Min(1,($bottom-$y)/25.0)
                $a = $src.A/255.0*$weight
                $dst = $baseFrame.GetPixel($x,$y)
                $outA = $a + $dst.A/255.0*(1-$a)
                if ($outA -le 0) { continue }
                $r = [int][Math]::Round(($src.R*$a+$dst.R*$dst.A/255.0*(1-$a))/$outA)
                $g = [int][Math]::Round(($src.G*$a+$dst.G*$dst.A/255.0*(1-$a))/$outA)
                $b = [int][Math]::Round(($src.B*$a+$dst.B*$dst.A/255.0*(1-$a))/$outA)
                $frame.SetPixel($x,$y,[System.Drawing.Color]::FromArgb([int][Math]::Round($outA*255),$r,$g,$b))
            }
        }
    }
    $frame.Save((Join-Path $outputDir ('idle_{0:000}.png' -f ($i+4))),[System.Drawing.Imaging.ImageFormat]::Png)
    $frame.Dispose()
}
for ($i = 4; $i -lt 8; $i++) {
    Copy-Item -LiteralPath (Join-Path $assetRoot ('eating-idle-chewing/idle_{0:000}.png' -f $i)) -Destination (Join-Path $outputDir ('idle_{0:000}.png' -f ($i+8)))
}
$baseFrame.Dispose()
$sheet.Dispose()
$lickPath = Join-Path $assetRoot 'eating-lick-sheet.png'
if (Test-Path -LiteralPath $lickPath) {
    $lickSheet = [System.Drawing.Bitmap]::new($lickPath)
    # Copy only the edited mouth area, preserving all existing registration.
    $patches = @(
        @{ Source=1; Target=5; X=217; Y=294; RX=24; RY=25 },
        @{ Source=2; Target=6; X=217; Y=352; RX=25; RY=28 },
        @{ Source=4; Target=8; X=217; Y=350; RX=25; RY=29 }
    )
    foreach ($patch in $patches) {
        $path = Join-Path $outputDir ('idle_{0:000}.png' -f $patch.Target)
        $loaded = [System.Drawing.Bitmap]::new($path)
        $frame = $loaded.Clone([System.Drawing.Rectangle]::new(0,0,443,443), [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $loaded.Dispose()
        $col = $patch.Source % 4
        $row = [int][Math]::Floor($patch.Source/4)
        $offsetX = [int][Math]::Round($col*$lickSheet.Width/4)
        $offsetY = [int][Math]::Round($row*$lickSheet.Height/2)
        for ($y=$patch.Y-$patch.RY; $y -le $patch.Y+$patch.RY; $y++) {
            for ($x=$patch.X-$patch.RX; $x -le $patch.X+$patch.RX; $x++) {
                $radius = [Math]::Sqrt([Math]::Pow(($x-$patch.X)/[double]$patch.RX,2)+[Math]::Pow(($y-$patch.Y)/[double]$patch.RY,2))
                if ($radius -ge 1) { continue }
                $weight = [Math]::Min(1,(1-$radius)/0.25)
                $src = $lickSheet.GetPixel($x+$offsetX,$y+$offsetY)
                $dst = $frame.GetPixel($x,$y)
                $r = [int][Math]::Round($dst.R*(1-$weight)+$src.R*$weight)
                $g = [int][Math]::Round($dst.G*(1-$weight)+$src.G*$weight)
                $b = [int][Math]::Round($dst.B*(1-$weight)+$src.B*$weight)
                $frame.SetPixel($x,$y,[System.Drawing.Color]::FromArgb($dst.A,$r,$g,$b))
            }
        }
        $tempPath = $path + '.new.png'
        $frame.Save($tempPath,[System.Drawing.Imaging.ImageFormat]::Png)
        $frame.Dispose()
        Move-Item -LiteralPath $tempPath -Destination $path -Force
    }
    $lickSheet.Dispose()
}
Write-Output 'Saved 16 frames: chewing, two bites, return, chewing.'
