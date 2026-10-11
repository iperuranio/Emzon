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
OPEN_FAILED_DETAIL = "{reason}. Prova con un altro file o controlla che non sia ancora in scrittura."
TOOL_MISSING = "Manca {tool}: reinstalla Emzon."
NO_VIDEO = "Il file non contiene un video"
UNKNOWN_DURATION = "Non si riesce a leggere la durata"
UNREADABLE = "Il file non è leggibile"
WAVEFORM_FAILED = "Onda non disponibile"
