from app.medication.dependencies import get_medication_service


async def consult_medication(condition: str, product_keyword: str) -> dict:
    """Retrieve grounded disease warnings and Long Châu products for consultation.

    Args:
        condition: The disease or health condition explicitly stated by the user.
        product_keyword: The Vietnamese product-search phrase derived from the request.

    Returns:
        Grounded knowledge, normalized products, limitations, and source status.
    """
    result = await get_medication_service().consult(condition, product_keyword)
    return result.model_dump(mode="json", by_alias=True, exclude_none=True)

