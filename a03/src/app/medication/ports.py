from typing import Protocol

from app.medication.models import GraphContext, LongChauSearchResult


class MedicationGraphRepository(Protocol):
    async def find_consultation_context(
        self,
        condition: str,
    ) -> GraphContext | None: ...


class ProductSearch(Protocol):
    async def search(self, keyword: str, limit: int) -> LongChauSearchResult: ...

