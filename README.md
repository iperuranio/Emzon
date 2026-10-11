# Emzon

[Italiano](#italiano) | [English](#english)

## Italiano

Emzon serve a una cosa sola: aprire una clip di gioco, togliere quello che non serve e salvarla, in pochi secondi.

Le registrazioni di NVIDIA ShadowPlay durano spesso minuti, ma quello che interessa sono gli ultimi secondi. Emzon apre il file, ti fa zoomare sul punto giusto, taglia testa e coda con un tasto e mette l'export in coda, così passi subito alla clip successiva.

**Stato:** in sviluppo, non ancora utilizzabile.

### Cosa fa

- Apre un video o una cartella, anche trascinandoli nella finestra. Si lavora su una clip alla volta.
- Taglio preciso al frame: `Q` taglia la testa, `W` la coda, alla posizione della testina.
- Gestisce più tracce audio, come quelle di ShadowPlay con gioco e microfono separati, con un volume per traccia.
- `Invio` salva il video accanto all'originale con `_edited` nel nome. `A` salva solo l'audio, per esempio per una soundboard.
- Gli export finiscono in una coda di rendering accelerata dalla GPU (NVENC), e intanto si continua a lavorare.
- Nelle impostazioni si sceglie una cartella fissa per gli export, oppure di sostituire l'originale mandandolo nel Cestino.

### Requisiti

- Windows 10 o 11, 64 bit
- Scheda video NVIDIA per l'encoding hardware

## English

Emzon does one thing: open a game clip, cut what you don't need, save it, in a few seconds.

NVIDIA ShadowPlay recordings often run for minutes while the part worth keeping is the last few seconds. Emzon opens the file, lets you zoom to the right spot, trims head and tail with a single key and queues the export, so you can move straight to the next clip.

**Status:** in development, not usable yet.

### Features

- Open a video or a whole folder, drag and drop included. One clip at a time.
- Frame-accurate trimming: `Q` cuts the head, `W` the tail, at the playhead.
- Multiple audio tracks, such as ShadowPlay's separate game and microphone tracks, each with its own volume.
- `Enter` saves the video next to the original with `_edited` in the name. `A` saves the audio only, for a soundboard for instance.
- Exports run in a GPU-accelerated render queue (NVENC) while you keep working.
- Settings let you pick a fixed export folder, or replace the original and move it to the Recycle Bin.

### Requirements

- Windows 10 or 11, 64-bit
- An NVIDIA graphics card for hardware encoding
