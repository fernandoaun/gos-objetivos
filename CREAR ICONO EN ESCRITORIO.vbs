' Crea un acceso directo en el Escritorio. Doble clic en este archivo una sola vez.
Option Explicit

Dim WshShell, FSO, root, desktop, vbsPath, iconPath, link, exitCode

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
root = FSO.GetParentFolderName(WScript.ScriptFullName)

vbsPath = root & "\ABRIR GOS Objetivos.vbs"
If Not FSO.FileExists(vbsPath) Then
    MsgBox "No se encuentra ABRIR GOS Objetivos.vbs", vbCritical, "GOS Objetivos"
    WScript.Quit 1
End If

exitCode = WshShell.Run("cmd /c cd /d """ & root & """ && python scripts\copiar_logo.py && python scripts\crear_icono.py", 0, True)
If exitCode <> 0 Then
    MsgBox "No se pudo preparar el logo para el icono." & vbCrLf & _
           "Verifica que Python este instalado.", vbExclamation, "GOS Objetivos"
End If

iconPath = root & "\static\img\gos-logo.ico"
desktop = WshShell.SpecialFolders("Desktop")
Set link = WshShell.CreateShortcut(desktop & "\GOS Objetivos.lnk")
link.TargetPath = vbsPath
link.WorkingDirectory = root
link.Description = "Abrir GOS Objetivos - Planeamiento Estrategico"
link.WindowStyle = 7
If FSO.FileExists(iconPath) Then
    link.IconLocation = iconPath & ",0"
End If
link.Save

If FSO.FileExists(iconPath) Then
    MsgBox "Listo." & vbCrLf & vbCrLf & _
           "En tu Escritorio: icono GOS Objetivos (logo GOS)." & vbCrLf & vbCrLf & _
           "Doble clic para abrir sin ventanas negras.", vbInformation, "GOS Objetivos"
Else
    MsgBox "Listo." & vbCrLf & vbCrLf & _
           "Acceso directo creado. Si el icono no muestra el logo," & vbCrLf & _
           "volve a ejecutar este archivo cuando exista gos-logo.png.", vbInformation, "GOS Objetivos"
End If
