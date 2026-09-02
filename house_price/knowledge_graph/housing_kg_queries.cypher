// ============================================================
// HOUSING KNOWLEDGE GRAPH — VERIFICATION / EXPLORATION QUERIES
// ============================================================

// 1) Tổng số entity
MATCH (h:HousingHouse)
OPTIONAL MATCH (h)-[:LOCATED_IN]->(d:HousingDistrict)
OPTIONAL MATCH (d)-[:BELONGS_TO]->(c:HousingCity)
RETURN
    count(DISTINCT h) AS houses,
    count(DISTINCT d) AS districts,
    count(DISTINCT c) AS cities;


// 2) Xem sample path House -> District -> City
MATCH (h:HousingHouse)-[:LOCATED_IN]->(d:HousingDistrict)-[:BELONGS_TO]->(c:HousingCity)
RETURN
    h.house_id AS house_id,
    h.title AS title,
    h.price_million_vnd AS price_million_vnd,
    d.name AS district,
    c.name AS city
LIMIT 20;


// 3) Số listing theo tỉnh/thành
MATCH (h:HousingHouse)-[:LOCATED_IN]->(:HousingDistrict)-[:BELONGS_TO]->(c:HousingCity)
RETURN
    c.name AS city,
    count(h) AS listings
ORDER BY listings DESC
LIMIT 20;


// 4) Giá trung bình theo tỉnh/thành
MATCH (h:HousingHouse)-[:LOCATED_IN]->(:HousingDistrict)-[:BELONGS_TO]->(c:HousingCity)
RETURN
    c.name AS city,
    count(h) AS listings,
    round(avg(h.price_million_vnd), 2) AS avg_price_million_vnd
ORDER BY avg_price_million_vnd DESC
LIMIT 20;


// 5) Giá trung bình theo quận/huyện với ít nhất 30 listing
MATCH (h:HousingHouse)-[:LOCATED_IN]->(d:HousingDistrict)-[:BELONGS_TO]->(c:HousingCity)
WITH
    d,
    c,
    count(h) AS listings,
    avg(h.price_million_vnd) AS avg_price
WHERE listings >= 30
RETURN
    d.name AS district,
    c.name AS city,
    listings,
    round(avg_price, 2) AS avg_price_million_vnd
ORDER BY avg_price_million_vnd DESC
LIMIT 30;


// 6) Tìm nhà theo điều kiện
MATCH (h:HousingHouse)-[:LOCATED_IN]->(d:HousingDistrict)-[:BELONGS_TO]->(c:HousingCity)
WHERE c.name = 'Hà Nội'
  AND h.area_m2 >= 50
  AND h.area_m2 <= 100
  AND h.price_million_vnd <= 10000
RETURN
    h.house_id,
    h.title,
    h.area_m2,
    h.bedrooms,
    h.bathrooms,
    h.floors,
    h.frontage,
    h.price_million_vnd,
    d.name AS district,
    c.name AS city
ORDER BY h.price_million_vnd ASC
LIMIT 50;
