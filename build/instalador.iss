; ============================================================
; Instalador de Windows para el Migrador de Catálogos (Inno Setup 6).
;
; Se arma con:
;     python build/build.py --con-audio --instalador
; o directamente:
;     ISCC build\instalador.iss /DMiVariante=completa /DMiRaiz=<ruta del repo>
;
; Decisiones que importan:
;
; - PrivilegesRequired=lowest. Instala en la carpeta del usuario y NO pide
;   permisos de administrador, así que no aparece el cartel de UAC. Es lo que
;   convierte la instalación en dos clics de verdad para cualquier persona.
;
; - LicenseFile con los términos de uso. Quien instala los acepta acá, y la app
;   los vuelve a mostrar la primera vez que se abre. Son el mismo texto.
;
; - El instalador tampoco está firmado, por la misma razón que el ejecutable.
;   SmartScreen puede avisar la primera vez; el README explica cómo seguir.
; ============================================================

#ifndef MiRaiz
  #define MiRaiz ".."
#endif
#ifndef MiVariante
  #define MiVariante "completa"
#endif
#ifndef MiVersion
  ; build.py la pasa leyendola de app/server.py. Si alguien corre ISCC a mano
  ; sin definirla, mejor que se note en el nombre a que mienta un numero.
  #define MiVersion "0.0.0-sin-definir"
#endif

#define MiNombre "Migrador de Catalogos"
#define MiNombreMostrado "Migrador de Catálogos"
#define MiAutor "Joaquín García Oliver"
#define MiSitio "https://github.com/joacogoliver-debug/catalog-migrator"

[Setup]
; Este GUID identifica a la aplicación entre versiones. No se cambia nunca: es
; lo que permite que una instalación nueva reemplace a la anterior en vez de
; dejar dos entradas en "Agregar o quitar programas".
AppId={{8F3C2A41-5E7D-4B96-9C18-2D6A0F4B7E53}
AppName={#MiNombreMostrado}
AppVersion={#MiVersion}
AppVerName={#MiNombreMostrado} {#MiVersion}
AppPublisher={#MiAutor}
AppPublisherURL={#MiSitio}
AppSupportURL={#MiSitio}/issues
AppUpdatesURL={#MiSitio}/releases
VersionInfoVersion={#MiVersion}
VersionInfoCompany={#MiAutor}
VersionInfoDescription={#MiNombreMostrado}

DefaultDirName={autopf}\{#MiNombre}
DefaultGroupName={#MiNombreMostrado}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

LicenseFile={#MiRaiz}\build\TERMINOS.txt
SetupIconFile={#MiRaiz}\app\web\assets\icono.ico
UninstallDisplayIcon={app}\{#MiNombre}.exe
WizardStyle=modern

OutputDir={#MiRaiz}\dist
OutputBaseFilename=Migrador-de-Catalogos-windows-{#MiVariante}-instalador
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos"

[Files]
Source: "{#MiRaiz}\dist\{#MiNombre}.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MiRaiz}\TERMINOS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MiRaiz}\LICENSE"; DestDir: "{app}"; DestName: "LICENCIA.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MiNombreMostrado}"; Filename: "{app}\{#MiNombre}.exe"
Name: "{group}\Desinstalar {#MiNombreMostrado}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MiNombreMostrado}"; Filename: "{app}\{#MiNombre}.exe"; Tasks: escritorio

[Run]
Filename: "{app}\{#MiNombre}.exe"; Description: "Abrir el Migrador de Catálogos"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; La carpeta de datos del usuario (clave de la API, diagnóstico, error.log) NO se
; borra a propósito. Si reinstala, se encuentra todo como lo dejó; y si de verdad
; quiere borrarla, está a la vista en su carpeta personal.
Type: files; Name: "{app}\TERMINOS.md"
Type: files; Name: "{app}\LICENCIA.txt"
