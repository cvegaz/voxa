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
