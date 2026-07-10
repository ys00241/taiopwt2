"""Photo service — photo upload, linking, and gallery logic."""


def process_upload(file_storage, year: int, entity_type: str | None = None,
                   entity_id: int | None = None) -> dict:
    """Process an uploaded photo file.

    Args:
        file_storage: Flask FileStorage object.
        year: Association year.
        entity_type: Optional entity type for linking.
        entity_id: Optional entity ID for linking.

    Returns:
        Dict with photo record info.
    """
    return {"id": 0, "filename": ""}


def get_photos_for_entity(entity_type: str, entity_id: int) -> list:
    """Get all photos linked to a given entity.

    Args:
        entity_type: e.g. 'item', 'member', 'this_year_item'.
        entity_id: The entity's ID.

    Returns:
        List of Photo dicts.
    """
    return []
