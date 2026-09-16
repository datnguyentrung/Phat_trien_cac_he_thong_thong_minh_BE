# Housing Knowledge Graph

## Graph schema

```text
(:House:HousingHouse:HousingKG)
        |
        | LOCATED_IN
        v
(:District:HousingDistrict:HousingKG)
        |
        | BELONGS_TO
        v
(:City:HousingCity:HousingKG)
```

Nguồn dữ liệu chỉ có `location` dạng `district, city/province`.
Vì vậy không tạo `Ward`, `School`, `Hospital`, `Road` hoặc quan hệ `NEAR`
nếu dataset không có dữ kiện hỗ trợ.

## Vì sao vẫn giữ `id`, `detail_url`, `title`, `timeline_hours` trong KG?

Preprocessor ML loại các cột này khỏi feature matrix.
Tuy nhiên knowledge graph có mục tiêu khác:
- `id` là định danh node ổn định;
- `detail_url` và `title` hỗ trợ provenance/traceability;
- `timeline_hours` là metadata của listing.

"Không dùng làm ML feature" không đồng nghĩa "không có giá trị trong KG".

## Cấu trúc file

Đặt 2 script trong:

```text
<project>/
  scripts/
    prepare_housing_kg.py
    load_housing_kg.py
  data/
    house_buying_dec29th_2025.csv
    nodes/
    relationships/
  config/
    neo4j.py
```

`config.neo4j.Neo4jClient` được tái sử dụng thông qua:

```python
driver = Neo4jClient.get_driver()
DATABASE = Neo4jClient.database_name
Neo4jClient.close_driver()
```

## Chạy

```bash
python scripts/prepare_housing_kg.py
python scripts/load_housing_kg.py
```

Load mặc định là idempotent bằng `MERGE`.

Nếu muốn xóa riêng subgraph Housing cũ trước khi load lại:

PowerShell:

```powershell
$env:HOUSING_KG_REPLACE="true"
python scripts/load_housing_kg.py
```

Batch size:

```powershell
$env:NEO4J_BATCH_SIZE="5000"
```

## Cleaning được đồng bộ với preprocessor Housing

- remove exact duplicates;
- remove missing target;
- remove target `<= 0`;
- normalize `location`;
- `frontage` về nullable integer;
- `area_m2`: 1..1,000,000;
- `bedrooms`, `bathrooms`, `floors`: 0..100;
- giá trị feature ngoài domain được chuyển thành missing;
- không tự động xóa target giá cao chỉ vì IQR.

Với file hiện tại, structural cleaning giữ lại khoảng 64k listing hợp lệ.
