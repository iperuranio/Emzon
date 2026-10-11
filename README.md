# Emzon

[Italiano](#italiano) | [English](#english)

## Italiano

Emzon serve a una cosa sola: aprire una clip di gioco, togliere quello che non serve e salvarla, in pochi secondi.

Le registrazioni di NVIDIA ShadowPlay durano spesso minuti, ma quello che interessa sono gli ultimi secondi. Emzon apre il file con la testina già vicino alla fine, ti fa zoomare sul punto giusto, taglia testa e coda con un tasto e mette l'export in coda, così passi subito alla clip successiva.

### Cosa fa

- Apre un video o una cartella, anche trascinandoli nella finestra. Si lavora su una clip alla volta e si passa alle altre della stessa cartella con `PagSu` e `PagGiù`, dalla più recente.
- Taglio preciso al fotogramma alla posizione della testina.
- Riproduce insieme tutte le tracce audio, come quelle di ShadowPlay con gioco e microfono separati, ognuna con il suo volume.
- Salva il video accanto all'originale con `_edited` nel nome, oppure solo l'audio (MP3, WAV o OGG), per esempio per una soundboard.
- Gli export finiscono in una coda: l'encoding usa NVENC della scheda NVIDIA, con l'encoding sulla CPU se NVENC non c'è, e intanto si continua a lavorare.
- Nelle impostazioni si sceglie una cartella fissa per gli export, oppure di sostituire l'originale mandandolo nel Cestino.

### Tasti

| Tasto | Azione |
| --- | --- |
| `Spazio` | Riproduci o ferma |
| `Q` | Taglia la testa alla testina |
| `W` | Taglia la coda alla testina |
| `Invio` | Salva il video |
| `A` | Salva solo l'audio |
| `←` `→` | Testina indietro o avanti di 1 secondo |
| `Maiusc` + `←` `→` | Un fotogramma indietro o avanti |
| `F` | Inquadra la selezione, di nuovo per tutto il file |
| `PagSu` `PagGiù` | Clip precedente o successiva |
| `1` … `9` | Silenzia o riattiva una traccia |
| `Ctrl` + `O` | Apri un file |

Sulla timeline la rotellina zooma attorno al cursore, `Maiusc` + rotellina o la rotella premuta spostano la vista, un clic sposta la testina senza avviare la riproduzione. Le linee di taglio si trascinano e il tasto destro le toglie.

L'anteprima può girare a 1/2, 1/4 o 1/8 della risoluzione per una riproduzione più fluida: Emzon ne prepara una copia leggera in background, mentre gli export usano sempre l'originale. Il pannello a sinistra mostra le clip della cartella e i dati di quella aperta.

### Installazione

Scarica `Emzon-Setup.exe` dall'[ultima release](https://github.com/iperuranio/Emzon/releases/latest) e avvialo: si installa per il tuo utente, senza permessi di amministratore, con la voce nel menu Start e in «Apri con» per i video. Si disinstalla dalle Impostazioni di Windows.

Windows potrebbe avvisare che l'app non è riconosciuta, perché non è firmata: scegli «Ulteriori informazioni» e poi «Esegui comunque».

Chi preferisce la versione portatile scarica `Emzon-win-x64.zip`, lo estrae in una cartella e avvia `Emzon.exe`.

Serve Windows 10 o 11 a 64 bit; per l'encoding hardware, una scheda NVIDIA.

## English

Emzon does one thing: open a game clip, cut what you don't need, save it, in a few seconds.

NVIDIA ShadowPlay recordings often run for minutes while the part worth keeping is the last few seconds. Emzon opens the file with the playhead already near the end, lets you zoom to the right spot, trims head and tail with a single key and queues the export, so you can move straight to the next clip.

### Features

- Open a video or a whole folder, drag and drop included. One clip at a time; `PgUp` and `PgDn` move through the rest of the folder, newest first.
- Frame-accurate trimming at the playhead.
- Every audio track plays at once, such as ShadowPlay's separate game and microphone tracks, each with its own volume.
- Save the video next to the original with `_edited` in the name, or the audio only (MP3, WAV or OGG), for a soundboard for instance.
- Exports run in a queue while you keep working, encoded with NVENC on NVIDIA cards and on the CPU otherwise.
- Settings let you pick a fixed export folder, or replace the original and move it to the Recycle Bin.

### Installation

Download `Emzon-Setup.exe` from the [latest release](https://github.com/iperuranio/Emzon/releases/latest) and run it: it installs for your user, without administrator rights, adds a Start menu entry and an "Open with" entry for videos, and uninstalls from Windows Settings.

Windows may warn that the app is unrecognised, because it is not signed: choose "More info", then "Run anyway".

For a portable copy, download `Emzon-win-x64.zip`, unzip it and run `Emzon.exe`.

Requires 64-bit Windows 10 or 11; hardware encoding needs an NVIDIA graphics card.

### Development

```
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m emzon
.venv/bin/python -m pytest
```

During development FFmpeg, FFprobe and libmpv come from the system (on macOS: `brew install ffmpeg mpv`). The Windows build bundles pinned copies; see `docs/architecture.md` and `THIRD_PARTY.md`.

## License

GPL-3.0. See `LICENSE` and `THIRD_PARTY.md`.
