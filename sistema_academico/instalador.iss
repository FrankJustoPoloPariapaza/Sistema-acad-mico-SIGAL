; Instalador opcional (Inno Setup 6: https://jrsoftware.org/isinfo.php).
; Primero ejecute build_exe.bat; luego abra este archivo en Inno Setup y pulse Compilar.
; Resultado: Output\Instalador_SistemaAcademico.exe
[Setup]
AppName=Sistema Academico
AppVersion=1.0
DefaultDirName={localappdata}\SistemaAcademico
DefaultGroupName=Sistema Academico
PrivilegesRequired=lowest
OutputBaseFilename=Instalador_SistemaAcademico
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\SistemaAcademico.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Sistema Academico"; Filename: "{app}\SistemaAcademico.exe"
Name: "{autodesktop}\Sistema Academico"; Filename: "{app}\SistemaAcademico.exe"

[Run]
Filename: "{app}\SistemaAcademico.exe"; Description: "Abrir el sistema"; Flags: nowait postinstall skipifsilent
