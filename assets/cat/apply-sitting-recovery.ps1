Add-Type -AssemblyName System.Drawing
$dir = Join-Path $PSScriptRoot 'sitting-idle'
$sheet = [System.Drawing.Bitmap]::new((Join-Path $PSScriptRoot 'sitting-recovery-sheet.png'))
$neutral = [System.Drawing.Bitmap]::new((Join-Path $dir 'idle_000.png'))
$lick = [System.Drawing.Bitmap]::new((Join-Path $dir 'idle_030.png'))
$noseX = @(162.41,158.23,153.57,146.46,164.12,156.94,151.75,146.31,164.27,157.41,151.90,146.03,165.60,158.99,152.73,146.21)
$noseY = @(103.98,104.97,106.21,105.30,102.01,101.93,103.19,104.39,103.75,106.03,106.40,107.64,106.69,106.22,107.26,104.54)
# Order real eyelid states by increasing aperture to avoid reopening/reclosing.
$eyeOrder = @(1,0,2,4,3,5,6,8,7,9,12,13,10,11,14,15)
# Extract the opaque pink tongue so it can physically shrink, not fade.
$tongue = [System.Drawing.Bitmap]::new(44,44,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$tongueOutline = [System.Drawing.Drawing2D.GraphicsPath]::new()
$points = [System.Drawing.PointF[]]@(
    [System.Drawing.PointF]::new(238,168), [System.Drawing.PointF]::new(245,159),
    [System.Drawing.PointF]::new(248,149), [System.Drawing.PointF]::new(253,144),
    [System.Drawing.PointF]::new(260,145), [System.Drawing.PointF]::new(267,151),
    [System.Drawing.PointF]::new(265,161), [System.Drawing.PointF]::new(260,170),
    [System.Drawing.PointF]::new(251,175), [System.Drawing.PointF]::new(243,172)
)
$tongueOutline.AddClosedCurve($points,[single]0.25)
for ($y=145; $y -lt 189; $y++) {
    for ($x=233; $x -lt 277; $x++) {
        $c = $lick.GetPixel($x,$y)
        if ($tongueOutline.IsVisible([single]$x,[single]$y)) {
            $tongue.SetPixel($x-233,$y-145,$c)
        }
    }
}
for ($i=0; $i -lt 16; $i++) {
    if ($i -eq 15) {
        Copy-Item -LiteralPath (Join-Path $dir 'idle_000.png') -Destination (Join-Path $dir 'idle_047.png') -Force
        continue
    }
    $frame = $neutral.Clone([System.Drawing.Rectangle]::new(0,0,443,443),[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    if ($i -lt 15) {
        $t = $i/15.0
        $source = $eyeOrder[$i]
        $col = $source%4
        $row = [int][Math]::Floor($source/4)
        $originX = [Math]::Round($col*$sheet.Width/4)+$noseX[$source]
        $originY = [Math]::Round($row*$sheet.Height/4)+$noseY[$source]
        # Only eyes and upper face use the newly generated true eyelid states.
        for ($y=78; $y -lt 150; $y++) {
            for ($x=138; $x -le 338; $x++) {
                $radius = [Math]::Sqrt([Math]::Pow(($x-238)/100.0,2)+[Math]::Pow(($y-146)/68.0,2))
                if ($radius -ge 1) { continue }
                $weight = [Math]::Min(1.0,(1-$radius)/0.20)
                $weight *= [Math]::Min(1.0,(150-$y)/8.0)
                $sx = [int][Math]::Round($originX+($x-238)/1.20)
                $sy = [int][Math]::Round($originY+($y-142)/1.20)
                $src = $sheet.GetPixel($sx,$sy)
                $dst = $neutral.GetPixel($x,$y)
                $r = [int][Math]::Round($dst.R*(1-$weight)+$src.R*$weight)
                $green = [int][Math]::Round($dst.G*(1-$weight)+$src.G*$weight)
                $b = [int][Math]::Round($dst.B*(1-$weight)+$src.B*$weight)
                $frame.SetPixel($x,$y,[System.Drawing.Color]::FromArgb($dst.A,$r,$green,$b))
            }
        }
        $scale = 1-$t*$t*(3-2*$t)
        $g = [System.Drawing.Graphics]::FromImage($frame)
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        # Anchor the tongue at the mouth while progressively curling it inward.
        $rect = [System.Drawing.RectangleF]::new([single](244-11*$scale),[single](161-16*$scale),[single](44*$scale),[single](44*$scale))
        $g.DrawImage($tongue,$rect)
        $g.Dispose()
    }
    $path = Join-Path $dir ('idle_{0:000}.png' -f (32+$i))
    $temp = $path+'.new.png'
    $frame.Save($temp,[System.Drawing.Imaging.ImageFormat]::Png)
    $frame.Dispose()
    Move-Item -LiteralPath $temp -Destination $path -Force
}
$tongue.Dispose()
$tongueOutline.Dispose()
$lick.Dispose()
$neutral.Dispose()
$sheet.Dispose()
Write-Output 'Replaced frames 032..047 with opaque eyelid states and geometric tongue retraction.'
