from apps.voices import storage


def generation_files(generation):
    """The stored files of one generation as (bucket, path) pairs."""
    audio = getattr(generation, "audio", None)
    if audio is None:
        return []
    return [(audio.storage_bucket, audio.file_path)]


def remove_generation_files(generation):
    """Delete the stored audio of one generation. Never raises (failures are logged as ORPHAN).

    Returns how many files were handed to storage for deletion.
    """
    files = generation_files(generation)
    if files:
        storage.remove_files(files)
    return len(files)
