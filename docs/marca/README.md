# Logo — Migrador de Catálogos

Símbolo: disco en semitono. La mitad izquierda (hueso o grafito según fondo) es el catálogo en origen; los puntos que cruzan el eje central son teal y se dispersan hacia la derecha: el catálogo ya migrado. ViewBox 92×64, proporción 23:16.

## Archivos
- symbol-positive.svg — grafito #141414 + teal-500 #387F7E, sobre hueso #F5F2ED
- symbol-negative.svg — hueso #F5F2ED + teal-400 #5DA09E, sobre grafito #141414 o teal-900 #0A2929
- symbol-on-teal.svg — hueso + grafito, sobre teal-500 (ícono de app, splash)
- lockup-positive.svg / lockup-negative.svg — símbolo + nombre en dos líneas
- Logo.jsx — componente React, mismos datos (variant: positive | negative | onTeal)

## Nombre
Archivo 600, tracking -0.02em, dos líneas ("Migrador" / "de Catálogos"), interlineado 1.05. Alto del nombre = alto del símbolo. Separación símbolo–texto = 1/4 del ancho del símbolo. Sobre hueso el texto va en grafito; sobre grafito, en hueso. Nunca en teal-500 (no cumple AA para texto chico).

## Reglas
- Tamaño mínimo del símbolo: 16 px de alto. A ese tamaño es el mismo SVG, sin versión pixelada.
- Área de respeto: 1 fila de puntos (7 unidades del viewBox) alrededor.
- No cambiar colores fuera de los tres pares de arriba. No rotar, no espejar: la migración va hacia la derecha.
- Favicon: symbol-on-teal.svg sobre un cuadrado teal-500, símbolo al 80% del ancho.
