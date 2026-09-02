# E-commerce Knowledge Graph

## Dataset

```text
Womens Clothing E-Commerce Reviews.csv
```

Primary ML task trong notebook:

```text
X = Age + Rating + Recommended IND
    + Positive Feedback Count + Combined Text

y = Department Name
```

Dataset **không có customer_id / transaction / purchase / cart history**.
Vì vậy KG không tạo node `Customer`, `Order`, `Cart` hoặc `Purchase`
nếu nguồn dữ liệu không hỗ trợ.

## Graph schema

```text
(:EcommerceReview)
       |
       | REVIEWS
       v
(:EcommerceProduct)

(:EcommerceReview)-[:ABOUT_DEPARTMENT]->(:EcommerceDepartment)

(:EcommerceReview)-[:IN_CLASS]->(:EcommerceClass)
                                      |
                                      | BELONGS_TO_DEPARTMENT
                                      v
                              (:EcommerceDepartment)

(:EcommerceReview)-[:IN_DIVISION]->(:EcommerceDivision)
```

### Vì sao Department/Class/Division vẫn có trong KG?

Trong pipeline ML, `Division Name` và `Class Name` bị loại khỏi feature set
vì chúng nằm trong cùng product hierarchy với target `Department Name`
và có thể gây **target leakage / shortcut learning**.

Trong knowledge graph, chúng không phải model input. Chúng là tri thức
phân loại thực tế có sẵn trong nguồn dữ liệu, vì vậy có thể lưu và truy vấn.

### Vì sao vẫn giữ `Clothing ID` và `Unnamed: 0`?

Hai cột này bị loại khỏi ML feature matrix vì là identifier.

Trong KG:
- `Unnamed: 0` được dùng để tạo `review_id` ổn định;
- `Clothing ID` được dùng để tạo `product_id`;
- đây là provenance/identity, không phải ML feature.

## Cleaning đồng bộ với notebook E-commerce

- remove exact duplicates;
- remove rows missing `Department Name`;
- normalize `Division Name`, `Department Name`, `Class Name`;
- missing `Title` / `Review Text` -> empty string;
- normalize whitespace;
- validate `Age`: 0 < Age <= 100;
- validate `Rating`: 1..5;
- validate `Recommended IND`: 0/1;
- validate `Positive Feedback Count`: >= 0;
- invalid numerical values -> missing;
- create `Combined Text`.

Với file hiện tại:
- raw rows: **23,486**;
- clean review rows: **23,472**;
- products: **1,199**;
- departments: **6**;
- classes: **20**;
- divisions: **3**.

Department distribution sau cleaning:
- Tops: 10,468
- Dresses: 6,319
- Bottoms: 3,799
- Intimate: 1,735
- Jackets: 1,032
- Trend: 119

## Cấu trúc project

Đặt 2 script trong:

```text
<project>/
  scripts/
    prepare_ecommerce_kg.py
    load_ecommerce_kg.py

  data/
    Womens Clothing E-Commerce Reviews.csv
    nodes/
    relationships/

  config/
    neo4j.py
```

`config.neo4j.Neo4jClient` được tái sử dụng:

```python
from config.neo4j import Neo4jClient

DATABASE = Neo4jClient.database_name
driver = Neo4jClient.get_driver()
...
Neo4jClient.close_driver()
```

## Chạy

```bash
python scripts/prepare_ecommerce_kg.py
python scripts/load_ecommerce_kg.py
```

Loader dùng `MERGE`, nên có thể chạy lại idempotent.

Nếu muốn xóa riêng subgraph E-commerce cũ trước khi load lại:

PowerShell:

```powershell
$env:ECOMMERCE_KG_REPLACE="true"
python scripts/load_ecommerce_kg.py
```

Batch size:

```powershell
$env:NEO4J_BATCH_SIZE="5000"
```

## Neo4j labels

```text
:EcommerceReview
:EcommerceProduct
:EcommerceDepartment
:EcommerceClass
:EcommerceDivision
:EcommerceKG
```

Namespace `EcommerceKG` giúp xóa riêng subgraph này mà không ảnh hưởng
Knowledge Graph của Diabetes hoặc Housing trong cùng database.
