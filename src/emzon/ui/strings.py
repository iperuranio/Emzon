"""Every string the interface shows."""

APP_NAME = "Emzon"

OPEN = "Apri file"
OPEN_TIP = "Apri un video (Ctrl+O)"
OPEN_DIALOG = "Apri un video"
VIDEO_FILTER = "Video (*.mp4 *.mkv *.mov *.webm *.avi);;Tutti i file (*)"

DROP_HINT = "Trascina qui una clip"

CUT_HEAD = "Taglia testa"
CUT_HEAD_TIP = "Taglia tutto prima della testina (Q)"
CUT_TAIL = "Taglia coda"
CUT_TAIL_TIP = "Taglia tutto dopo la testina (W)"
PLAY = "Riproduci"
PAUSE = "Ferma"
PLAY_TIP = "Riproduci o ferma (Spazio)"
SELECTION = "Selezione"

VIEW_OF = "di"
VIEW_TIP = "Parte del file visibile. Rotella: zoom sul cursore. Maiusc+rotella: scorri. F: inquadra la selezione"
OVERVIEW_TIP = "File intero. Clic o trascina: sposta la vista. Doppio clic: tutto"
START = "Inizio"
END = "Fine"
MUTE_TIP = "Silenzia (tasto {key})"
VOLUME_TIP = "Volume. Doppio clic: 100%"


def track_name(position: int, title: str | None) -> str:
    return title or f"Traccia {position + 1}"


LOADING = "Apertura…"
OPEN_FAILED = "Impossibile aprire «{name}»"
TOOL_MISSING = "Manca {tool} nella cartella di Emzon. Reinstalla Emzon."
NO_VIDEO = "Il file non contiene una traccia video. Apri un file video."
UNKNOWN_DURATION = "La durata non è leggibile. Se il gioco sta ancora registrando, aspetta che finisca."
UNREADABLE = "FFmpeg non riesce a leggerlo: il file è danneggiato o ancora in scrittura."
WAVEFORM_FAILED = "Onda non disponibile"

EXPORT_FAILED = "FFmpeg non ha completato l’export"

SAVE_VIDEO = "Salva video"
SAVE_VIDEO_TIP = "Salva la selezione come video (Invio)"
SAVE_AUDIO = "Salva audio"
SAVE_AUDIO_TIP = "Salva solo l’audio della selezione (A)"
PREVIOUS_TIP = "Clip precedente (PagSu)"
NEXT_TIP = "Clip successiva (PagGiù)"
SETTINGS = "Impostazioni"
VIDEO_LANE = "Video"

QUEUE_TIP = "Coda di rendering"
QUEUE_CLEAR = "Rimuovi completati"
JOB_WAITING = "In attesa"
JOB_FINISHING = "Sostituzione…"
JOB_FAILED = "Non riuscito"
JOB_CANCELLED = "Annullato"
JOB_CANCEL = "Annulla"
JOB_REVEAL = "Mostra nella cartella"
JOB_SOFTWARE = "NVENC non disponibile: encoding sulla CPU"
JOB_KEPT = "L’originale non è stato spostato nel Cestino ({error}): l’export è salvato come copia"
JOB_REPLACE_BUSY = "Una sostituzione di questo file è già in coda: l’export è salvato come copia"

DESTINATION = "Destinazione"
DESTINATION_BESIDE = "Accanto all’originale"
DESTINATION_FOLDER = "Cartella fissa"
CHOOSE_FOLDER = "Scegli cartella…"
CHOOSE_FOLDER_DIALOG = "Cartella per gli export"
VIDEO_SAVE = "Salva video"
VIDEO_SAVE_COPY = "Crea una copia"
VIDEO_SAVE_REPLACE = "Sostituisci l’originale"
VIDEO_SAVE_REPLACE_TIP = "Il file originale va nel Cestino e al suo posto resta la versione tagliata"
AUDIO_FORMAT = "Formato audio"

NO_CLIPS = "Nessuna clip in «{name}»"
NO_CLIPS_DETAIL = "La cartella non contiene video .mp4, .mkv, .mov, .m4v, .webm o .avi."
QUIT_TITLE = "Export in corso"
QUIT_TEXT = "Chiudendo Emzon gli export in coda vengono annullati."
QUIT_CONFIRM = "Chiudi e annulla"
QUIT_KEEP = "Resta aperto"
CUT_HANDLE_TIP = "Trascina per spostare il taglio. Tasto destro: rimuovi il taglio"
LENGTH = "Durata"
PREVIEW = "Anteprima"
PREVIEW_TIP = "Risoluzione dell’anteprima. Più bassa è, più fluidi sono riproduzione e trascinamento; l’export usa sempre l’originale"
PREVIEW_PREPARING = "Preparazione dell’anteprima {scale}: {percent}%"
PREVIEW_FULL = "Piena"
PREVIEW_RESOLUTION = "Risoluzione dell’anteprima"
ABOUT = "Emzon {version}, di {author}"
AUTHOR = "Claudio Portuesi (Metessi)"
PREVIEW_FAILED = "Anteprima leggera non disponibile, si usa l’originale: {reason}"
FOLDER_TIP = "Clip della cartella"
FOLDER_COUNT = "{count} clip nella cartella"
DETAIL_LABELS = {
    "length": "Durata",
    "resolution": "Risoluzione",
    "fps": "Fotogrammi",
    "codec": "Codec",
    "audio": "Tracce audio",
    "size": "Peso",
    "date": "Data",
}
