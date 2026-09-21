# Instalar el Migrador en una Mac

**Español** · [English](INSTALAR-MAC.en.md)

Cinco minutos. Hay que usar la Terminal un momento, pero es copiar y pegar.

---

## 1. Fijate qué Mac tenés

Menú  (arriba a la izquierda) → **Acerca de esta Mac**.

- Si dice **Chip Apple M1 / M2 / M3 / M4** → tenés una Mac **Apple Silicon**.
- Si dice **Procesador Intel** → tenés una Mac **Intel**.

Esto importa: son dos archivos distintos y **no funciona el que no es**.

## 2. Bajá el archivo

Entrá a **[Releases](https://github.com/joacogoliver-debug/catalog-migrator/releases)**
y, en la versión de más arriba, abrí **Assets**. Bajá:

| Tu Mac | El archivo |
|---|---|
| Apple Silicon | `Migrador-de-Catalogos-macos-apple-silicon-completa` |
| Intel | `Migrador-de-Catalogos-macos-intel-completa` |

Es un archivo grande (unos 60 MB) y sin extensión. Queda en **Descargas**.

> `completa` trae todo y ya viene con la clave de YouTube configurada: se abre y
> funciona. `esencial` es más liviana, pero te pide tu propia clave.

## 3. Abrilo desde la Terminal

Abrí la Terminal (Cmd+Espacio, escribí `Terminal`, Enter) y pegá **estas tres
líneas, una por vez**. Si tenés una Mac Intel, cambiá `apple-silicon` por `intel`
en las tres.

```bash
cd ~/Downloads
chmod +x Migrador-de-Catalogos-macos-apple-silicon-completa
xattr -c Migrador-de-Catalogos-macos-apple-silicon-completa
```

Y ahora sí, para abrir la app:

```bash
./Migrador-de-Catalogos-macos-apple-silicon-completa
```

La app se abre en su propia ventana; en algunas Mac, en tu navegador. Las dos
cosas son normales y funcionan igual. **Dejá la Terminal abierta**: si la
cerrás, se cierra la app.

De acá en adelante, para volver a abrirla alcanza con las dos líneas del final
(`cd ~/Downloads` y `./Migrador...`). Lo de `chmod` y `xattr` es una sola vez.

---

## Si algo sale mal

**`bad CPU type in executable`**
Bajaste el archivo de la otra arquitectura. Volvé al punto 1.

**«no se puede abrir porque no se puede verificar al desarrollador»**
Te faltó la línea del `xattr -c`. Corrigela y probá de nuevo.

Si insiste: **Ajustes del Sistema → Privacidad y seguridad**, bajá hasta el final
y apretá **"Abrir de todos modos"**. Aparece sólo después del primer intento
bloqueado.

**`No such file or directory`**
El archivo no está en Descargas, o el nombre no es exactamente ese. En la
Terminal escribí `ls ~/Downloads/Migrador*` y fijate cómo se llama de verdad.

**`Permission denied`**
Te faltó la línea del `chmod +x`.

**No pasa nada, o querés saber qué encontró**
Corré esto y mandale el resultado a Joaco:

```bash
./Migrador-de-Catalogos-macos-apple-silicon-completa --diagnostico
```

Escribe un reporte de qué puede hacer la app en tu máquina y lo guarda en
`~/.migrador-catalogos/diagnostico.txt`.

---

## Por qué la Mac desconfía

El programa **no está firmado** con un certificado de Apple. Firmar cuesta una
cuota anual y la herramienta es gratis. No significa que sea inseguro: el código
es público y el ejecutable se compila en GitHub, a la vista, desde ese código.

Si preferís no pelearte con nada de esto, se puede correr desde el código fuente
con dos comandos: está en el [README](../README.md#correrla-desde-el-código).
