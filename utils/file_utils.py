from config import SUPPORTED_IMAGE_TYPES, MAX_IMAGE_SIZE_MB


def validate_image(uploaded_file):
    """
    Validate the uploaded image before sending it to Gemini.

    Returns:
        (True, "") if valid
        (False, error_message) if invalid
    """

    if uploaded_file is None:
        return False, "Please upload an image."

    file_name = uploaded_file.name.lower()

    extension = file_name.split(".")[-1]

    if extension not in SUPPORTED_IMAGE_TYPES:
        return False, "Unsupported image format."

    file_size_mb = uploaded_file.size / (1024 * 1024)

    if file_size_mb > MAX_IMAGE_SIZE_MB:
        return False, (
            f"Image is too large. "
            f"Maximum allowed size is {MAX_IMAGE_SIZE_MB} MB."
        )

    return True, ""
