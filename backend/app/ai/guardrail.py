async def validate_submission_content(content: str) -> bool:
    if not content:
        return False
    if len(content) > 10000:
        return False
    return True
