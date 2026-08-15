"""Custom exceptions for the services layer."""


class LLMUnavailableError(Exception):
    """Raised when the LLM API is unreachable due to network/timeout errors."""

    def __init__(self, detail: str = "El servicio LLM no está disponible en este momento."):
        self.detail = detail
        self.error_code = "LLM_UNAVAILABLE"
        super().__init__(self.detail)


class LLMInvalidResponseError(Exception):
    """Raised when the LLM returns an empty or invalid response."""

    def __init__(self, detail: str = "La respuesta del LLM es vacía o inválida."):
        self.detail = detail
        self.error_code = "LLM_INVALID_RESPONSE"
        super().__init__(self.detail)


class AudioUnreadableError(Exception):
    """Raised when the uploaded audio cannot be decoded well enough to measure it.

    ADR-0019 makes the recording cap a measurement of the FILE rather than a
    client-reported number. A file we cannot measure therefore cannot be admitted:
    letting it through would restore exactly the hole the ADR closes, since an
    unmeasurable file is indistinguishable from one hiding an hour of audio. We fail
    closed and never pay Whisper for it.
    """

    def __init__(
        self,
        detail: str = "No se pudo leer el archivo de audio. Vuelve a grabar la narración.",
    ):
        self.detail = detail
        self.error_code = "AUDIO_UNREADABLE"
        super().__init__(self.detail)


class DemoBudgetExhaustedError(Exception):
    """Raised when the public demo has reached its daily or monthly USD ceiling.

    Deliberately NOT phrased as a server fault: hitting this means real demand
    arrived (ADR-0019 §3). The message invites the visitor to leave an email, so
    the worst moment of the system becomes its best point of capture, and the owner
    widens the caps with a configuration edit.
    """

    def __init__(
        self,
        detail: str = (
            "La demostración gratuita alcanzó su cupo. "
            "Déjanos tu correo y te damos acceso."
        ),
    ):
        self.detail = detail
        self.error_code = "DEMO_BUDGET_EXHAUSTED"
        super().__init__(self.detail)


class WhisperUnavailableError(Exception):
    """Raised when the Whisper API is unreachable due to network/timeout errors."""

    def __init__(self, detail: str = "El servicio Whisper no está disponible en este momento."):
        self.detail = detail
        self.error_code = "WHISPER_UNAVAILABLE"
        super().__init__(self.detail)


class WhisperEmptyResponseError(Exception):
    """Raised when the Whisper API returns an empty transcription."""

    def __init__(self, detail: str = "Whisper retornó una transcripción vacía."):
        self.detail = detail
        self.error_code = "WHISPER_EMPTY_RESPONSE"
        super().__init__(self.detail)


class WhisperNoSpeechError(Exception):
    """Raised when the Whisper API detects no speech in the audio."""

    def __init__(self, detail: str = "No se detectó habla en el audio proporcionado."):
        self.detail = detail
        self.error_code = "WHISPER_NO_SPEECH"
        super().__init__(self.detail)
