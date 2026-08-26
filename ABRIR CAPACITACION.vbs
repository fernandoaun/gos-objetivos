' Inicia GOS Capacitación (puerto 5002) sin ventanas negras.
Option Explicit

Dim WshShell, FSO, root, exitCode, capDb

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
root = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = root

exitCode = WshShell.Run("cmd /c python --version", 0, True)
If exitCode <> 0 Then
    MsgBox "No esta instalado Python." & vbCrLf & vbCrLf & _
           "Instala desde https://www.python.org/downloads/" & vbCrLf & _
           "Marca: Add python.exe to PATH", vbCritical, "GOS Capacitación"
    WScript.Quit 1
End If

capDb = root & "\instance\capacitacion\gos_cap.db"
If Not FSO.FileExists(capDb) Then
    MsgBox "No existe la base de Capacitación:" & vbCrLf & capDb & vbCrLf & vbCrLf & _
           "Ejecutá primero SEPARAR CAPACITACION.bat", vbExclamation, "GOS Capacitación"
    WScript.Quit 1
End If

WshShell.Run "cmd /c for /f ""tokens=5"" %a in ('netstat -aon 2^>nul ^| findstr "":5002"" ^| findstr ""LISTENING""') do taskkill /F /PID %a >nul 2>&1", 0, True

WshShell.Run "cmd /c cd /d """ & root & """ && pythonw run_capacitacion.py", 0, False

WScript.Sleep 4000
WshShell.Run "http://127.0.0.1:5002/", 1, False
