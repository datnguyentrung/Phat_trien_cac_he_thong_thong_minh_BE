from functools import cache

from app.medication.long_chau import LongChauClient
from app.medication.neo4j_repository import Neo4jMedicationRepository
from app.medication.service import MedicationConsultationService
from config.settings import settings


@cache
def get_graph_repository() -> Neo4jMedicationRepository:
    return Neo4jMedicationRepository.create(
        uri=settings.NEO4J_URI,
        username=settings.NEO4J_USERNAME,
        password=settings.NEO4J_PASSWORD,
        database=settings.NEO4J_DATABASE,
    )


@cache
def get_long_chau_client() -> LongChauClient:
    return LongChauClient(
        api_url=settings.LONG_CHAU_API_URL,
        web_base_url=settings.LONG_CHAU_WEB_BASE_URL,
        timeout_seconds=settings.LONG_CHAU_TIMEOUT_SECONDS,
    )


@cache
def get_medication_service() -> MedicationConsultationService:
    return MedicationConsultationService(
        graph_repository=get_graph_repository(),
        product_search=get_long_chau_client(),
        search_limit=settings.LONG_CHAU_SEARCH_LIMIT,
        summary_limit=settings.LONG_CHAU_SUMMARY_LIMIT,
    )


async def close_medication_dependencies() -> None:
    if get_long_chau_client.cache_info().currsize:
        await get_long_chau_client().close()
    if get_graph_repository.cache_info().currsize:
        await get_graph_repository().close()
    get_medication_service.cache_clear()
    get_long_chau_client.cache_clear()
    get_graph_repository.cache_clear()
