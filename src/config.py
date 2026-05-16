import os
import sys

from dotenv import load_dotenv
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import create_client, Client

load_dotenv()


class Settings(BaseSettings):
    # Infrastructure — required
    SUPABASE_URL:        str = Field(..., min_length=1)
    SUPABASE_KEY:        str = Field(..., min_length=1)
    GOOGLE_GENAI_API_KEY: str = Field(default="")

    # Connector credentials — optional (managed via UI / merchant_credentials table)
    GOOGLE_SERVICE_ACCOUNT_JSON: str | None = Field(default=None)
    GOOGLE_SHEET_IDS:            str | None = Field(default=None)
    SHOPIFY_STORE_URL:           str | None = Field(default=None)
    SHOPIFY_API_KEY:             str | None = Field(default=None)
    META_ACCESS_TOKEN:           str | None = Field(default=None)
    META_AD_ACCOUNT_ID:          str | None = Field(default=None)

    # AI keys — optional
    GROQ_API_KEY:                str = Field(default="")
    AGENT_CHECK_INTERVAL_MINUTES: int = Field(default=1440)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        print("\n Environment configuration error\n")
        for error in e.errors():
            field   = ".".join(map(str, error["loc"]))
            message = error["msg"]
            print(f"• {field}: {message}")
        print("\nSet SUPABASE_URL and SUPABASE_KEY in your .env file.\n")
        sys.exit(1)


settings: Settings = load_settings()
supabase: Client   = create_client(str(settings.SUPABASE_URL), settings.SUPABASE_KEY)
