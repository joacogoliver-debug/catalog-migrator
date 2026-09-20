# Catalog Migrator — visual world

[Español](DESIGN.md) · **English**

Durable decisions. What the product is, and does not change, lives in
`PRODUCT.en.md`.

What is kept from the brand is what matters: **graphite, bone and the teal ramp**.
Everything else (typography, shape, density, components) is decided here.

The direction came out of a concrete reference: a web template made by the
designer at the company where I work. Dark, full black, hairline cards, mono
labels anchored to the edge and states as tinted fill. What follows is that
grammar translated into an inventory tool, which is a rather different thing from
that piece.

---

## 1. The concept: graphite is the surface

The app does not draw gray boxes on a gray background. The canvas is **graphite
taken down to almost black**, and the working surfaces **are the brand's
graphite**. The main card of every screen is literally the brand color, not a
gray borrowed from some system.

That leaves one consequence that orders the rest: **if the surfaces are that
close together, they cannot be separated by a step of gray.** They are separated
by a one-pixel border at very low opacity. That is what lets black stay black and
keeps the screen from filling with gray rectangles in different tones.

**Three gestures hold it up, and none of them is decorative.**

**The border.** Every block is a hairline card with a title band on top. Depth
comes from the border, not from a blur: there are no shadows anywhere in the app.

**The anchored label.** Everything that labels rather than reads goes in mono,
small caps and wide tracking, resting against the edge of the screen: the footer,
the action bar's summary, the table headers, the field labels. It is the app's
voice for what is not content.

**The digit.** Everything that gets counted or compared goes in mono with
`tabular-nums`: ISRC, UPC, years, durations, quantities. They are half the
screen, and treating them as running text was the original mistake.

**The grid.** Two 1 px lines at very low opacity over the canvas. It is not there
to simulate a plane: it is there so emptiness has scale when a view has little
content.

## 2. Light

**Dark by default.** It comes from the scene of use, not from the category: this
app gets opened at night to do inventory work. Light exists in full and is picked
from the header.

Light does **not** come from the reference, which is dark only. It is built with
the same grammar, inverted: the canvas is bone taken down, the cards are bone,
and the borders are graphite at low opacity.

## 3. Color

| Role | Value |
|---|---|
| Graphite | `#141414` |
| Bone | `#F5F2ED` |
| Teal | `#387F7E`, ramp 50 to 900 |
| Neutrals | warm-temperature grays, hue 82 |
| Semantic | negative `#E3645E`, attention `#E1A536`, positive `#60AC6D` (in light they drop to `#A82E2F`, `#7E5500`, `#2C6539`) |

Three rules of use.

**Teal is the only accent.** It marks what is actionable and what is in flight.
Its most visible place is the circle of the active step in the header, which is
what you see on every screen.

**The primary is not colored.** The main button is solid bone over graphite. It
is the lightest thing on the screen and that is why it is the first thing seen,
with no need to paint it.

**States are tinted fill, not border.** A badge is the semantic color itself
mixed at 13% into the surface, with saturated text of the same tone on top.
Neither a colored border nor a pastel fill: the flat patch is the shortcut that
makes everything look alike.

**All of it was measured.** The worst text-over-surface pair gives 4.7 in dark
and 4.9 in light, both above the AA minimum. The 500 neutrals were left out of
the text roles because they gave 3.6 and 3.7.

## 4. Typography

Two families, not three.

**Public Sans** for interface, body and headings. **DM Mono** for data, codes and
the labels anchored to the edge.

The heading is **large and light**: 44 px at weight 300. That contrast against a
14 px interface at weight 400 is what builds the hierarchy. There is no need to
shout in bold if the scale already says it.

| Role | Size | Family |
|---|---|---|
| View title | 44 px | Public Sans 300 |
| Section title | 15 px | Public Sans 500 |
| Body and interface | 14 px | Public Sans 400 |
| Data and code | 13 px | DM Mono |
| Badge | 11 px | Public Sans 500 |
| Anchored label | 10 px | DM Mono, small caps, tracking 0.14em |

Negative tracking belongs to the heading only. The mono labels need the
opposite, and quite a lot of it: that is what turns them into an edge marking and
not just small text.

Both families are SIL Open Font License 1.1 and travel inside the executable, 56
KB in total. The latin subset covers Spanish and English in full, which are the
app's two languages; the ℗ symbol, which shows up in one validation message, is
resolved by the system font.

**English is shorter than Spanish**, almost always, and that matters in the two
places where width is fixed: the anchored mono labels with 0.14em tracking and
the buttons in the action bar. No measurement in the system was calculated
against the length of the Spanish text: the buttons grow with their content and
the labels do not truncate.

## 5. Shape

A single family of radii, small ones: **6 px** on badges and marks, **8 px** on
controls, **12 px** on cards. The app does not float over anything, so there is
no outer container radius.

**Zero shadows.** Separation is done by the one-pixel border. Shadow is reserved
for what really floats, which today is nothing.

**Zero colored side border.** An alert's accent is its tinted fill and its text.

## 6. Surfaces

| Level | Dark | Light |
|---|---|---|
| Canvas | `#0A0A09` | `#E8E4DC` |
| Card | `#141414` (graphite) | `#F5F2ED` (bone) |
| Title band, hover | `#1E1D1C` | `#EDEAE3` |
| Border | bone at 10% | graphite at 12% |
| Soft border | bone at 5% | graphite at 6% |

## 7. Motion

**One single authored moment**: the long job. Three dots of the logo pulsing in
sequence while it runs, the new log lines coming in with a fade, and when it ends
the pulse goes out, a check appears and half a second later the view changes.
That is what separates "it finished" from "the screen changed all at once".

Everything else is immediate response to the pointer or the keyboard, at 100 ms:
the checkbox's check drawing itself, the detail unfolding, the view entering when
the step changes. `prefers-reduced-motion` turns all of it off.

## 8. The surfaces I did not draw

They get themed, because they come with values that belong to no system and it
shows: text selection, the writing caret, scrollbars, the focus ring, the
`accent-color` of native controls and the underline on links.

## 9. What is forbidden in this world

Not out of dogma, but because we already tried it and it is what made the app
look like every other one.

- Shadows to separate blocks. The border does that.
- Steps of gray as structure. The surfaces sit almost together on purpose.
- Light pastel fill on badges, and badges with a colored border.
- The metric template: huge number, small label, row of stats.
- Small caps as page structure. They go only on what labels.
- Emojis as icons.
- Gradients, frosted glass and colored glows.
- Pure black `#000000`: the canvas is graphite taken down, and it is warm.

## 10. What could not be carried over from the reference

Worth writing down, because it is going to be asked again.

The reference is a **marketing landing page**: isometric 3D renders, scroll that
pins sections, 120 px headlines, pricing plans. None of that has anywhere to land
in a tool that shows 46 tracks in a table and lives in a desktop window with
fixed chrome.

What did land: the full black with the grid, the hairline cards, the numbered
index in circles (which fit the four steps exactly), the mono labels anchored to
the edge, the large scale at light weight, and the dark-fill chips with saturated
text.
