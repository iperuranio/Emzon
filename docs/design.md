# Design

The reference for how Emzon looks and behaves. When the code and this file disagree, one of them is wrong: fix it in the same change.

## Principles

- One clip at a time. The window always shows exactly one file.
- Every frequent action has one key and one visible control. Nothing asks for confirmation unless it destroys data.
- The timeline never misleads: how much of the file is visible, where the file really starts and ends, and what has been cut are always readable at a glance.
- Nothing runs while nobody is looking. A hidden or unfocused window that is not playing does no work.

## Layout

From top to bottom:

1. **Header** (56 px). Left: `Apri` (a labelled button, the most important action), a divider, the folder panel toggle (a small icon), previous clip, position in the folder (`3/14`), next clip, file name. Right: the half-resolution preview toggle (quiet: no frame, violet text when on), render queue (present only while it holds jobs), settings (a gear). Controls appear only when they have something to act on: with no clip open, the header holds the settings alone.
2. **Stage.** The video, 16:9, centred, rounded 12 px.
3. **Timeline panel.** Overview, zoom funnel, ruler, video lane, one lane per audio track, transport bar.

The track gutter on the left of the timeline is 150 px wide and holds each track's name, volume and mute control.

## Timeline

### Zoom and orientation

- **Overview.** The whole file, always. It is exactly as wide as the file appears in the fully zoomed out timeline below it. It shows cut parts hatched, the kept part tinted with violet bars standing out of the bar at its ends, the visible window as a white frame and the playhead as a white line with a dark halo and a caret above the bar.
- **Funnel.** Two lines join the edges of the visible window in the overview to the edges of the file in the detail view. Fully zoomed out they are vertical; zooming in makes them converge on the magnified part.
- **Readout.** Left of the overview: the length of the file currently visible, then the total (`12,0 s di 5:00`).
- **File ends.** The detail view may run up to 2% past either end of the file. A real start or end is drawn as a rounded cap with a brighter edge and labelled `Inizio` or `Fine` on the ruler. Where the clip continues beyond the view, the lanes fade out at the edge instead.
- **Cut parts** stay where they are, hatched. The timeline is never folded or rescaled around the selection, so its scale always matches the file.

### Mouse

- **Wheel** zooms around the mouse cursor, not around the playhead. Minimum visible span: 0.5 s.
- **Shift + wheel** and horizontal scrolling pan the view.
- **Click** moves the playhead. It never starts or stops playback: paused stays paused, playing continues from the new point.
- **Drag** scrubs. Playback, if it was running, pauses during the drag and resumes on release.
- **Dragging past either edge** of a zoomed view scrolls it, faster the further the pointer goes.
- **Middle button drag** moves the view.
- **Cut lines:** the pointer turns into a horizontal resize cursor over them; dragging moves the cut (the frame under it shows in the player), right click removes it. A cut never crosses the other one.
- **Overview:** click or drag centres the view on that point; double click shows the whole file.

### Keyboard

| Key | Action |
| --- | --- |
| `Space` | Play or pause |
| `Q` | Cut the head at the playhead |
| `W` | Cut the tail at the playhead |
| `Enter` | Save the video |
| `A` | Save the audio only |
| `←` `→` | Move the playhead by 1 s |
| `Shift` + `←` `→` | Move the playhead by one frame |
| `F` | Fit the selection; press again for the whole file |
| `PgUp` `PgDn` | Previous or next clip in the folder |
| `Ctrl` + `O` | Open a file or folder |
| `1` to `9` | Mute or unmute track n |

`Q` and `W` also work during playback, cutting where the playhead is at that instant. Cutting the head past the current tail resets the tail to the end of the file, and the reverse.

The two cut actions also have buttons on either side of the play button: `Taglia testa` on the left, `Taglia coda` on the right, each showing its key. These three sit in the exact middle of the bottom bar, whenever the window is wide enough; the playhead time, `Durata` and `Selezione` are on the left, the save buttons on the right.

Clip length and selection read in whole seconds (`10 s`, `5:00`); only the playhead time keeps hundredths.

## Preview resolution

A toggle in the header, `Anteprima 1/2`, also in the settings. When on, the player uses a half-resolution copy of the clip made of keyframes only; the clip plays at full resolution until the copy is ready, then switches without losing position or play state. A ring on the toggle shows the preparation; exports always use the original. Lower fractions are not offered: below half resolution a game clip stops being readable.

## Folder panel

The panel toggle in the header slides a 360 px panel in from the left, pushing the video aside. On top, the open clip's details: length, resolution, frame rate, codec, audio tracks, size, date. Below, every clip of the folder as a tile, two per row: a frame from three quarters into the clip, its name, its length and size; the open one has a violet frame. A click opens a clip. The panel remembers whether it was open.

## Unreadable files

Files too small to hold a video (under 16 KB, such as recordings that were never finished) are left out of a folder. A clip that turns out unreadable while browsing, opening a folder or reading the folder's details is dropped from the folder and Emzon moves on in the same direction; the error page appears only for a file opened on purpose, or when nothing readable is left. The error states the file, then what went wrong and what to do, wrapped over as many lines as it needs.

## Opening files

- A file or folder can be opened from the header or dropped anywhere on the window. Dropping replaces the clip being edited, without asking.
- A folder opens its most recent clip first. `PgUp` and `PgDn` move through the others.
- The open dialogs, for files and for folders, start in the folder of the last clip opened, remembered across restarts; the first time, and whenever that folder is gone, they start in the system Videos folder.
- A clip remembers its cut points for the session, so coming back to it restores them.
- A new clip opens with the playhead near the end, where the interesting part usually is.

## Saving

- **Video** (`Enter`): a copy next to the original named `<name>_edited.<ext>`. If that name exists, `<name>_edited (2).<ext>` and so on. The frame under the playhead when the tail was cut is the last frame of the export.
- **Audio** (`A`): the mix of all tracks with their current volumes. MP3 by default; the format is a setting.
- Settings can send every export to one fixed folder, or replace the original and move the original to the Recycle Bin.
- Every export goes to the render queue and editing continues immediately. A finished job shows a check and a button to reveal the file in Explorer; a failed one turns red with the reason in its tooltip.
- The queue's ring sits in the header only while the queue holds jobs. `Rimuovi completati` clears what has finished.
- Closing the window while exports are running asks first; the safe choice, staying open, is the default.

## Tokens

### Colour

| Token | Value | Use |
| --- | --- | --- |
| `bg` | `#0E0C13` | Window |
| `panel` | `#14111B` | Timeline panel |
| `lane` | `#1A1622` | Lanes, popovers |
| `raised` | `#1E1A28` | Hover, chips |
| `line` | `#2A2535` | Separators, slider tracks |
| `line-strong` | `#6B5F8A` | File start and end |
| `text` | `#ECE8F4` | Primary text, playhead |
| `muted` | `#9A93AB` | Secondary text, icons |
| `faint` | `#7E7791` | Ruler labels |
| `accent` | `#9B7BFF` | Primary action, cut handles, progress |
| `accent-soft` | `#B9A4FF` | Accent text on dark |
| `on-accent` | `#120E1A` | Text on accent |
| `track-1` | `#A88BFF` | First audio track |
| `track-2` | `#D9CCFF` | Second audio track |
| `ok` | `#8FE3B0` | Finished job |
| `error` | `#FF8A9A` | Failures |

Further tracks continue the violet scale, alternating lightness so neighbours stay distinguishable.

### Type

- **Geist** for the interface, **Geist Mono** for every time value, so digits never shift width.
- Sizes: 20 px playhead time, 14 px file name and buttons, 13 px labels, 12 px values, 11 px ruler and key caps.

### Shape

- Radii: lanes 6 px, buttons 10 px, popovers 14 px, the video 12 px.
- Icons: 1.75 px stroke, round caps and joins.

## Copy

- The interface is in Italian. All strings live in one module so other languages can be added.
- Sentence case, real accents, «caporali», the `…` character.
- Times as `m:ss,cc` (`4:16,40`), durations under a minute as seconds (`10,00 s`). Decimal comma.
- Every visible string is a label, a value, a state or an action. Explanations go in tooltips.
- Controls read verb plus object (`Taglia testa`, `Salva video`). Errors say what happened, why, and what to do.

## States

- **Empty:** the app icon, `Trascina qui una clip o una cartella`, `Apri file` (primary, `Ctrl+O`) beside `Apri cartella` (`Ctrl+Maiusc+O`), and `Riapri «cartella»` for the last folder used, when it still exists. No panel, no clip controls.
- **Dragging a file over the window:** a violet frame over the whole window.
- **Loading:** the previous view stays until the clip is ready; `Apertura…` appears only if opening takes longer than 300 ms.
- **Error:** the file name in red, then what went wrong and what to do, in one sentence.
- **No audio:** only the video lane; `Salva audio` is disabled.
- **Waveform not readable:** the lane says `Onda non disponibile`.
- **Settings:** three choices (destination, what saving a video does, audio format), each a segmented control, applied at once.
