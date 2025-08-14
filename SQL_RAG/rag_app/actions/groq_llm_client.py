



def _get_llm_client() -> Groq:
    """Return an authenticated Groq client.

    Tries several common env-var names (useful if the key is stored as, e.g.,
    GROQ_KEY or GROQ_TOKEN). Provides a clear hint if none are found.
    """

    api_key = (
        os.getenv("GROQ_API_KEY")
        or os.getenv("GROQ_KEY")
        or os.getenv("GROQ_TOKEN")
    )

    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not found. Please set it in your environment or a .env file."
        )

    return Groq(api_key=api_key)

