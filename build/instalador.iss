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

; LicenseFile no va acá sino en [Languages], uno por idioma: quien instala en
; inglés tiene que poder leer lo que está aceptando.
SetupIconFile={#MiRaiz}\app\web\assets\icono.ico
UninstallDisplayIcon={app}\{#MiNombre}.exe
WizardStyle=modern

; Con dos idiomas Inno pregunta cuál usar antes de empezar. Se fuerza el diálogo
; en vez de dejarlo en "auto" porque auto lo saltea cuando el idioma del sistema
; coincide con uno de los dos, y entonces quien tiene Windows en español no
; llega a ver que el inglés existe.
ShowLanguageDialog=yes

OutputDir={#MiRaiz}\dist
OutputBaseFilename=Migrador-de-Catalogos-windows-{#MiVariante}-instalador
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
; El español va primero porque es el idioma del proyecto y el que Inno propone
; por defecto. Cada uno con sus términos: es lo que se acepta al instalar.
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"; LicenseFile: "{#MiRaiz}\build\TERMINOS.txt"
Name: "en"; MessagesFile: "compiler:Default.isl"; LicenseFile: "{#MiRaiz}\build\TERMS.txt"

[CustomMessages]
es.CrearAcceso=Crear un acceso directo en el escritorio
en.CrearAcceso=Create a desktop shortcut
es.AccesosDirectos=Accesos directos
en.AccesosDirectos=Shortcuts
es.AbrirApp=Abrir el Migrador de Catálogos
en.AbrirApp=Open Catalog Migrator
es.Desinstalar=Desinstalar
en.Desinstalar=Uninstall

[Tasks]
Name: "escritorio"; Description: "{cm:CrearAcceso}"; GroupDescription: "{cm:AccesosDirectos}"

[Files]
Source: "{#MiRaiz}\dist\{#MiNombre}.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MiRaiz}\TERMINOS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MiRaiz}\TERMS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MiRaiz}\LICENSE"; DestDir: "{app}"; DestName: "LICENCIA.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MiNombreMostrado}"; Filename: "{app}\{#MiNombre}.exe"
Name: "{group}\{cm:Desinstalar} {#MiNombreMostrado}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MiNombreMostrado}"; Filename: "{app}\{#MiNombre}.exe"; Tasks: escritorio

[Run]
Filename: "{app}\{#MiNombre}.exe"; Description: "{cm:AbrirApp}"; Flags: nowait postinstall skipifsilent

[Code]
{ El idioma elegido acá queda como el de la app. Se deja en un idioma.txt al
  lado del ejecutable y NO en la config del usuario: la config es donde vive lo
  que la persona eligió dentro de la app, y pisarla desde el instalador le
  cambiaría una decisión propia cada vez que actualiza.

  El servidor lo lee en `idioma_del_instalador()` y lo usa sólo como valor
  inicial: apenas alguien toca el selector de la cabecera, manda la config. }
procedure CurStepChanged(CurStep: TSetupStep);
var
  Codigo: String;
begin
  if CurStep = ssPostInstall then
  begin
    if ActiveLanguage = 'en' then
      Codigo := 'en'
    else
      Codigo := 'es';
    SaveStringToFile(ExpandConstant('{app}\idioma.txt'), Codigo, False);
  end;
end;

[UninstallDelete]
; La carpeta de datos del usuario (clave de la API, diagnóstico, error.log) NO se
; borra a propósito. Si reinstala, se encuentra todo como lo dejó; y si de verdad
; quiere borrarla, está a la vista en su carpeta personal.
Type: files; Name: "{app}\TERMINOS.md"
Type: files; Name: "{app}\TERMS.md"
Type: files; Name: "{app}\LICENCIA.txt"
Type: files; Name: "{app}\idioma.txt"
