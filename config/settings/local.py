from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------

DEBUG = True

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="IuhcGAcLVLAQLHLAmRtViGRZ49zxbw0i62ZDYk0ezz97sWDTTCYGnbmTEtAoRFic",
)

ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]
