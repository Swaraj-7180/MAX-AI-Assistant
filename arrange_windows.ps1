Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

# Wait until 3 chrome windows are open (max 30 seconds)
$timeout = 30
$elapsed = 0
while ($elapsed -lt $timeout) {
    $wins = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 }
    if ($wins.Count -ge 3) { break }
    
    # Try edge if chrome not found
    $wins = Get-Process msedge -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 }
    if ($wins.Count -ge 3) { break }

    Start-Sleep -Seconds 1
    $elapsed++
}

$handles = $wins | Select-Object -ExpandProperty MainWindowHandle | Select-Object -Last 3

$positions = @(
    @{X=0;    Y=0;   W=960;  H=520},
    @{X=960;  Y=0;   W=960;  H=520},
    @{X=0;    Y=520; W=1920; H=520}
)

for ($i = 0; $i -lt [Math]::Min($handles.Count, 3); $i++) {
    $hwnd = $handles[$i]
    $p = $positions[$i]
    [Win32]::ShowWindow($hwnd, 1)
    [Win32]::MoveWindow($hwnd, $p.X, $p.Y, $p.W, $p.H, $true)
}