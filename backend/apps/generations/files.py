from apps.voices import storage


def remove_generation_files(generation):
    """Delete the stored audio of one generation. Never raises (failures are logged as ORPHAN).

    Returns how many files were handed to storage for deletion.
    """
    audio = getattr(generation, "audio", None)
    if audio is None:
        return 0
    storage.remove_files([(audio.storage_bucket, audio.file_path)])
    return 1
