from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Application configuration settings loaded from environment or .env file."""
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Audio specifications
    SAMPLE_RATE: int = 16000          # 16 kHz
    CHANNELS: int = 1                 # Mono
    SAMPLE_WIDTH: int = 2             # 16-bit PCM = 2 bytes per sample
    CHUNK_SIZE: int = 512             # 512 samples = 32ms at 16kHz
    
    # Loopback / Echo mode (useful for audio round-trip testing)
    ENABLE_LOOPBACK: bool = False
    
    # API Keys (optional for Milestone 1)
    GROQ_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    DEEPGRAM_API_KEY: str | None = None
    CARTESIA_API_KEY: str | None = None
    
    @property
    def bytes_per_chunk(self) -> int:
        """Expected byte length of an audio chunk."""
        return self.CHUNK_SIZE * self.CHANNELS * self.SAMPLE_WIDTH

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
