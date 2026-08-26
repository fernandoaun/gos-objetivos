' Inicia GOS Objetivos sin ventanas negras (consola oculta).
' Si existe instance\objetivos\gos.db (separación Cap), usa modo objetivos.
Option Explicit

Dim WshShell, FSO, root, exitCode, objDb, runner

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
root = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = root

exitCode = WshShell.Run("cmd /c python --version", 0, True)
If exitCode <> 0 Then
    MsgBox "No esta instalado Python." & vbCrLf & vbCrLf & _
           "Instala desde https://www.python.org/downloads/" & vbCrLf & _
           "Marca: Add python.exe to PATH", vbCritical, "GOS Objetivos"
    WScript.Quit 1
End If

WshShell.Run "cmd /c for /f ""tokens=5"" %a in ('netstat -aon 2^>nul ^| findstr "":5001"" ^| findstr ""LISTENING""') do taskkill /F /PID %a >nul 2>&1", 0, True

exitCode = WshShell.Run("cmd /c cd /d """ & root & """ && python scripts\actualizar.py", 0, True)
If exitCode <> 0 Then
    MsgBox "Error al actualizar GOS Objetivos." & vbCrLf & _
           "Revisa que Python funcione correctamente.", vbCritical, "GOS Objetivos"
    WScript.Quit 1
End If

objDb = root & "\instance\objetivos\gos.db"
If FSO.FileExists(objDb) Then
    runner = "pythonw run_objetivos.py"
Else
    runner = "pythonw run.py"
End If

WshShell.Run "cmd /c cd /d """ & root & """ && " & runner, 0, False

WScript.Sleep 5000
WshShell.Run "http://127.0.0.1:5001/", 1, False
