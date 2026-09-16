# Diabetes Knowledge Graph — BRFSS 2023

Bộ file này được dựng từ:
- `diabetes_binary_5050split_health_indicators_BRFSS2023.csv`
- logic structural cleaning trong `preprocessor(2).ipynb`

## Kiến trúc KG

- `(:Respondent)` — một người trả lời khảo sát BRFSS.
- `(:Concept)` — một khái niệm/feature nhị phân như HighBP, Smoker, Diabetes...
- `(Respondent)-[:HAS_INDICATOR {value: 0|1}]->(Concept)`

Các biến `BMI`, `MentHlth`, `PhysHlth`, `GenHlth`, `AgeGroup`, `Education`, `Income`
được lưu làm property của `Respondent`.

Lưu ý: không gọi node là `Patient`, vì dữ liệu này là dữ liệu khảo sát.

## Cây thư mục nên đặt

```text
your-project/
├── data/
│   ├── raw/
│   │   └── diabetes_binary_5050split_health_indicators_BRFSS2023.csv
│   ├── nodes/
│   │   ├── respondents.csv
│   │   └── concepts.csv
│   ├── relationships/
│   │   └── respondent_concepts.csv
│   └── diabetes_clean_for_kg.csv
├── notebooks/
│   └── preprocessor.ipynb
├── scripts/
│   ├── build_kg_data.py
│   └── import_neo4j.py
├── schema.cypher
├── requirements.txt
└── .env.example
```

## Quy tắc làm sạch bám notebook

1. Xóa exact duplicate.
2. Chỉ giữ target `Diabetes_binary` thuộc `{0,1}`.
3. `KidneyDisease`, `Asthma`, `COPD`: `1 -> 1`, `2 -> 0`; mã khác -> missing.
4. Binary 0/1: mã ngoài `{0,1}` -> missing.
5. Ordinal:
   - GenHlth: 1..5
   - AgeGroup: 1..13
   - Education: 1..6
   - Income: 1..11
6. Continuous:
   - BMI: 10..100
   - MentHlth: 0..30
   - PhysHlth: 0..30
7. Không xóa outlier chỉ vì IQR.
8. KG lưu giá trị semantic gốc; không lưu StandardScaler output vì scaler là representation cho model, không phải tri thức miền.

## Cách dùng

### 1. Cài dependency

```bash
pip install -r requirements.txt
```

### 2. Đặt dataset gốc

Copy file vào:

```text
data/raw/diabetes_binary_5050split_health_indicators_BRFSS2023.csv
```

### 3. Nếu muốn sinh lại CSV của KG

```bash
python scripts/build_kg_data.py
```

Bộ ZIP này đã có sẵn các CSV được sinh ra nên bước này không bắt buộc.

### 4. Cấu hình Neo4j

PowerShell:

```powershell
$env:NEO4J_URI="neo4j://localhost:7687"
$env:NEO4J_USERNAME="neo4j"
$env:NEO4J_PASSWORD="YOUR_PASSWORD"
$env:NEO4J_DATABASE="neo4j"
```

### 5. Import

```bash
python scripts/import_neo4j.py
```

Script sẽ tạo constraint/index rồi MERGE node + relationship theo batch.

## Kiểm tra trong Neo4j Browser

```cypher
MATCH (n) RETURN labels(n), count(*) ORDER BY count(*) DESC;
```

```cypher
MATCH ()-[r]->() RETURN type(r), count(*) ORDER BY count(*) DESC;
```

Ví dụ xem người có diabetes và high blood pressure:

```cypher
MATCH (r:Respondent)-[d:HAS_INDICATOR]->(diabetes:Concept {feature:'Diabetes_binary'}),
      (r)-[bp:HAS_INDICATOR]->(highbp:Concept {feature:'HighBP'})
WHERE d.value = 1 AND bp.value = 1
RETURN r.respondent_id, r.bmi, r.age_group, r.general_health
LIMIT 50;
```

## Thống kê bộ dữ liệu KG đã sinh

- Raw rows: 71,814
- Clean respondents: 70,841
- Concept nodes: 16
- Indicator relationships: 1,132,793
