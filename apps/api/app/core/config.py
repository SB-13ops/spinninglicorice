from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder default secrets that must never be used in production. Startup
# validation (below) refuses to boot a production app that still carries them.
INSECURE_PLACEHOLDERS = {"", "change-me-in-production", "change-me"}
INSECURE_TOKEN_KEY = "dev-insecure-token-key-change-me-0000000000="


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "SpinningLicorice"
    database_url: str = "postgresql+psycopg://spinninglicorice:spinninglicorice@localhost:5432/spinninglicorice"

    discogs_consumer_key: str = ""
    discogs_consumer_secret: str = ""
    discogs_callback_url: str = "http://localhost:8000/api/v1/integrations/discogs/callback"
    discogs_user_agent: str = "SpinningLicorice/0.1"
    discogs_oauth_temp_secret: str = "change-me-in-production"

    openai_api_key: str = ""
    concert_provider_api_key: str = ""
    ticketmaster_api_key: str = ""

    # --- Anthropic AI (Claude) ---
    # When set, SpinningLicorice uses Claude for natural-language hunt parsing, result
    # explanations, and web-search-backed enrichment. When empty, every AI
    # feature degrades gracefully to its non-AI fallback (e.g. the regex parser),
    # so the app runs fine without a key.
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    # Cheap, fast model for structured extraction and short explanations.
    ai_fast_model: str = Field(default="claude-haiku-4-5", validation_alias="AI_FAST_MODEL")
    # More capable model for web-search-backed research.
    ai_research_model: str = Field(default="claude-sonnet-5", validation_alias="AI_RESEARCH_MODEL")
    # Hard cap on web searches per enrichment request (each search costs money).
    ai_web_search_max_uses: int = Field(default=3, validation_alias="AI_WEB_SEARCH_MAX_USES")

    # --- Authentication (JWT) ---
    # JWT_SECRET_KEY signs access tokens. It MUST be set to a strong random
    # value in production (e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`).
    # The default below is only tolerated when APP_ENV=development.
    jwt_secret_key: str = Field(
        default="dev-insecure-jwt-secret-change-me",
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # --- Secrets at rest ---
    # Fernet key used to encrypt third-party OAuth tokens (e.g. Discogs) before
    # they are written to the database. Generate one with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # The default below is a well-known DEV key and is rejected in production.
    token_encryption_key: str = Field(
        default="dev-insecure-token-key-change-me-0000000000=",
        validation_alias="TOKEN_ENCRYPTION_KEY",
    )

    # --- Social login (Google / Facebook OAuth) ---
    # Obtain these from the Google Cloud Console and Facebook developer console.
    # The redirect/callback URIs registered there must match:
    #   <API_BASE_URL>/api/v1/auth/google/callback
    #   <API_BASE_URL>/api/v1/auth/facebook/callback
    google_client_id: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", validation_alias="GOOGLE_CLIENT_SECRET")
    facebook_client_id: str = Field(default="", validation_alias="FACEBOOK_CLIENT_ID")
    facebook_client_secret: str = Field(default="", validation_alias="FACEBOOK_CLIENT_SECRET")
    # Public base URL of THIS api (used to build the OAuth redirect_uri).
    api_base_url: str = Field(default="http://localhost:8000", validation_alias="API_BASE_URL")

    # Public base URL of the web app, used to build shareable invite / public
    # links (e.g. https://spinninglicorice-web.up.railway.app). Falls back to the first
    # CORS origin if unset.
    web_base_url: str = Field(default="http://localhost:3000", validation_alias="WEB_BASE_URL")

    # --- Trip planner (Concert road trips) ---
    # Your Expedia affiliate/creator tracking ID, once approved at
    # creator.expediagroup.com/affiliates. When set, booking deep-links carry
    # your tag so eligible bookings earn commission; when empty, links are plain
    # (still working) Expedia searches.
    expedia_affiliate_id: str = Field(default="", validation_alias="EXPEDIA_AFFILIATE_ID")

    # --- Affiliate / referral revenue (Concert + trip) ---
    # Each is optional and independent. When set, the matching outbound links
    # carry your tracking tag and earn commission on qualifying actions; when
    # empty, the app links to the partner normally (no revenue, still works).
    ticket_affiliate_provider: str = Field(default="", validation_alias="TICKET_AFFILIATE_PROVIDER")  # seatgeek|stubhub|vividseats|ticketmaster
    ticket_affiliate_id: str = Field(default="", validation_alias="TICKET_AFFILIATE_ID")
    car_affiliate_provider: str = Field(default="", validation_alias="CAR_AFFILIATE_PROVIDER")  # expedia|rentalcars|discovercars
    car_affiliate_id: str = Field(default="", validation_alias="CAR_AFFILIATE_ID")
    rideshare_provider: str = Field(default="", validation_alias="RIDESHARE_PROVIDER")  # uber|lyft
    rideshare_referral_url: str = Field(default="", validation_alias="RIDESHARE_REFERRAL_URL")

    # Fallback national-average gas price ($/gallon) used when the user hasn't
    # set their own and AI lookup is unavailable.
    default_gas_price_usd: float = Field(default=3.50, validation_alias="DEFAULT_GAS_PRICE_USD")

    # --- Redis (OAuth request-token state, caching) ---
    # When set, transient OAuth state is stored in Redis so it survives restarts
    # and works across multiple replicas. When empty, an in-process fallback is
    # used (fine for a single local dev process, NOT for production).
    redis_url: str = Field(default="", validation_alias="REDIS_URL")

    # Comma-separated list of allowed browser origins for CORS. In production
    # set this to the deployed web app's origin, e.g.
    #   CORS_ALLOW_ORIGINS=https://spinninglicorice-web.up.railway.app
    # Multiple origins are comma-separated. Defaults to the local Next.js dev
    # server.
    cors_allow_origins_raw: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ALLOW_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file="../../.env", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @model_validator(mode="after")
    def _fail_fast_on_insecure_production(self) -> "Settings":
        """Refuse to start a production app that still uses placeholder secrets.

        A missing or default JWT secret in production would let anyone forge
        access tokens, so we fail loudly at startup rather than silently
        booting an insecure server.
        """
        if self.is_production:
            problems = []
            if (
                self.jwt_secret_key in INSECURE_PLACEHOLDERS
                or self.jwt_secret_key == "dev-insecure-jwt-secret-change-me"
            ):
                problems.append("JWT_SECRET_KEY")
            elif len(self.jwt_secret_key.encode()) < 32:
                # HS256 needs a >= 32-byte secret to be sound; PyJWT warns below
                # this. Only enforced in production so local dev with the short
                # default secret still runs.
                problems.append("JWT_SECRET_KEY (must be at least 32 bytes)")
            if self.discogs_oauth_temp_secret in INSECURE_PLACEHOLDERS:
                problems.append("DISCOGS_OAUTH_TEMP_SECRET")
            if self.token_encryption_key in INSECURE_PLACEHOLDERS or self.token_encryption_key == INSECURE_TOKEN_KEY:
                problems.append("TOKEN_ENCRYPTION_KEY")
            if problems:
                raise ValueError(
                    "Insecure configuration for production (APP_ENV="
                    f"{self.app_env}): the following must be set to strong, "
                    f"non-default values: {', '.join(problems)}. "
                    'Generate a strong secret with: python -c "import secrets; '
                    'print(secrets.token_urlsafe(48))"'
                )
        return self

    @property
    def cors_allow_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allow_origins_raw.split(",")
            if origin.strip()
        ]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Return a driver-qualified URL suitable for SQLAlchemy/psycopg.

        Managed Postgres providers (Railway, Heroku, Render, etc.) expose a
        DATABASE_URL that starts with ``postgres://`` or ``postgresql://``.
        SQLAlchemy needs the driver spelled out (``postgresql+psycopg://``)
        to select psycopg 3. Normalize here so both the app engine and the
        Alembic migration environment share one source of truth.
        """
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


settings = Settings()
