import sys

from dotenv import load_dotenv
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import create_client, Client

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    SUPABASE_URL: str = Field(..., min_length=1)
    SUPABASE_KEY: str = Field(..., min_length=1)

    GOOGLE_SERVICE_ACCOUNT_JSON: str = Field(..., min_length=1)
    GOOGLE_SHEET_IDS: str = Field(..., min_length=1)
    GOOGLE_GENAI_API_KEY: str = Field(..., min_length=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


def load_settings() -> Settings:
    """
    Load and validate application settings.
    """

    try:
        return Settings()

    except ValidationError as e:

        print("\n❌ Environment configuration error\n")

        for error in e.errors():

            field = ".".join(map(str, error["loc"]))
            message = error["msg"]

            print(f"• {field}: {message}")

        print("\nPlease check your .env file.\n")

        sys.exit(1)


# Validated settings
settings = load_settings()


# Supabase client
supabase: Client = create_client(
    str(settings.SUPABASE_URL),
    settings.SUPABASE_KEY,
)
