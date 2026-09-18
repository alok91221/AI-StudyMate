import time

from google import genai

from config import GEMINI_MODEL_FALLBACK_CHAIN


class GeminiQuotaError(Exception):
    """Raised when all configured Gemini models are rate limited."""
    pass


class GeminiTemporaryError(Exception):
    """Raised when Gemini is temporarily unavailable."""
    pass


def create_gemini_client(api_key):
    """Create and return a Gemini client."""

    return genai.Client(
        api_key=api_key
    )


def _is_quota_error(error_message):
    """Check whether an error indicates a quota/rate-limit problem."""

    quota_indicators = [
        "429",
        "RESOURCE_EXHAUSTED",
        "quota",
        "rate limit",
        "rate_limit"
    ]

    error_text = error_message.lower()

    return any(
        indicator.lower() in error_text
        for indicator in quota_indicators
    )


def _is_temporary_error(error_message):
    """Check whether an error indicates a temporary service problem."""

    temporary_indicators = [
        "503",
        "UNAVAILABLE",
        "500",
        "502",
        "504"
    ]

    error_text = error_message.upper()

    return any(
        indicator in error_text
        for indicator in temporary_indicators
    )


def _generate_with_model(
    client,
    model,
    contents
):
    """
    Generate content using one Gemini model.

    Returns:
        (response_text, model_name)
    """

    max_attempts = 3

    for attempt in range(max_attempts):

        try:

            response = client.models.generate_content(
                model=model,
                contents=contents
            )

            return response.text, model

        except Exception as error:

            error_message = str(error)

            if _is_quota_error(error_message):

                raise GeminiQuotaError(
                    f"Model '{model}' reached its quota "
                    f"or rate limit."
                ) from error

            if _is_temporary_error(error_message):

                if attempt < max_attempts - 1:

                    wait_time = 5 * (2 ** attempt)

                    time.sleep(wait_time)

                    continue

                raise GeminiTemporaryError(
                    f"Gemini model '{model}' is "
                    f"temporarily unavailable."
                ) from error

            raise GeminiTemporaryError(
                f"Gemini request failed for model "
                f"'{model}'."
            ) from error


def generate_content_with_retry(
    client,
    contents
):
    """
    Try Gemini models in the configured fallback order.

    Returns:
        (response_text, model_name)
    """

    quota_models = []

    for model in GEMINI_MODEL_FALLBACK_CHAIN:

        try:

            return _generate_with_model(
                client,
                model,
                contents
            )

        except GeminiQuotaError:

            quota_models.append(model)

            continue

    model_list = ", ".join(quota_models)

    raise GeminiQuotaError(
        "All configured Gemini models have "
        "reached their current quota or rate limit. "
        f"Models checked: {model_list}"
    )


def analyze_images(
    client,
    images,
    prompt
):
    """
    Analyze one or more images with Gemini.

    Returns:
        (response_text, model_name)
    """

    contents = [prompt]

    for image in images:

        image_part = genai.types.Part.from_bytes(
            data=image["image_bytes"],
            mime_type=image["mime_type"]
        )

        contents.append(image_part)

    return generate_content_with_retry(
        client,
        contents
    )
