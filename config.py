# ---------------------------------------------------------
# AI StudyMate Configuration
# ---------------------------------------------------------


# ---------------------------------------------------------
# Gemini model fallback chain
# ---------------------------------------------------------
#
# The app tries these models in order.
#
# If the current model reaches a quota/rate limit,
# the app automatically tries the next model.
#
# All models below support image input.
#

GEMINI_MODEL_FALLBACK_CHAIN = [
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
]


# ---------------------------------------------------------
# Default Gemini model
# ---------------------------------------------------------

GEMINI_MODEL = GEMINI_MODEL_FALLBACK_CHAIN[0]


# ---------------------------------------------------------
# Supported image formats
# ---------------------------------------------------------

SUPPORTED_IMAGE_TYPES = [
    "jpg",
    "jpeg",
    "png"
]


# ---------------------------------------------------------
# Maximum image size
# ---------------------------------------------------------

MAX_IMAGE_SIZE_MB = 10


# ---------------------------------------------------------
# Maximum number of images per study session
# ---------------------------------------------------------

MAX_IMAGES_PER_SESSION = 5