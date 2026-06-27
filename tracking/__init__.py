"""AirWrite Studio tracking package.

Keep this package initializer lightweight. Importing optional voice support here
forces Vosk to load during app startup, which can break packaged builds before
the main window appears.
"""
