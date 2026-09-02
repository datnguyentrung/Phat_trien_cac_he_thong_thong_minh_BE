// ============================================================
// E-COMMERCE KNOWLEDGE GRAPH — VERIFICATION / EXPLORATION
// ============================================================

// 1) Tổng số entity
MATCH (r:EcommerceReview)
OPTIONAL MATCH (r)-[:REVIEWS]->(p:EcommerceProduct)
OPTIONAL MATCH (r)-[:ABOUT_DEPARTMENT]->(d:EcommerceDepartment)
OPTIONAL MATCH (r)-[:IN_CLASS]->(c:EcommerceClass)
OPTIONAL MATCH (r)-[:IN_DIVISION]->(v:EcommerceDivision)
RETURN
    count(DISTINCT r) AS reviews,
    count(DISTINCT p) AS products,
    count(DISTINCT d) AS departments,
    count(DISTINCT c) AS classes,
    count(DISTINCT v) AS divisions;


// 2) Xem sample path Review -> Product / Department / Class / Division
MATCH (r:EcommerceReview)-[:REVIEWS]->(p:EcommerceProduct)
MATCH (r)-[:ABOUT_DEPARTMENT]->(d:EcommerceDepartment)
MATCH (r)-[:IN_CLASS]->(c:EcommerceClass)
MATCH (r)-[:IN_DIVISION]->(v:EcommerceDivision)
RETURN
    r.review_id AS review_id,
    p.clothing_id AS clothing_id,
    r.age AS age,
    r.rating AS rating,
    r.recommended_ind AS recommended,
    r.positive_feedback_count AS positive_feedback_count,
    left(r.review_text, 180) AS review_preview,
    d.name AS department,
    c.name AS class_name,
    v.name AS division
LIMIT 20;


// 3) Phân bố review theo Department Name
MATCH (r:EcommerceReview)-[:ABOUT_DEPARTMENT]->(d:EcommerceDepartment)
RETURN
    d.name AS department,
    count(r) AS reviews
ORDER BY reviews DESC;


// 4) Rating / recommendation trung bình theo Department
MATCH (r:EcommerceReview)-[:ABOUT_DEPARTMENT]->(d:EcommerceDepartment)
RETURN
    d.name AS department,
    count(r) AS reviews,
    round(avg(r.rating), 3) AS avg_rating,
    round(avg(r.recommended_ind), 3) AS recommendation_rate,
    round(avg(r.positive_feedback_count), 3) AS avg_positive_feedback
ORDER BY reviews DESC;


// 5) Class hierarchy
MATCH (c:EcommerceClass)-[:BELONGS_TO_DEPARTMENT]->(d:EcommerceDepartment)
RETURN
    d.name AS department,
    collect(c.name) AS classes
ORDER BY department;


// 6) Sản phẩm có nhiều review nhất
MATCH (r:EcommerceReview)-[:REVIEWS]->(p:EcommerceProduct)
RETURN
    p.clothing_id AS clothing_id,
    count(r) AS review_count,
    round(avg(r.rating), 3) AS avg_rating,
    round(avg(r.recommended_ind), 3) AS recommendation_rate
ORDER BY review_count DESC
LIMIT 30;


// 7) Review có nhiều positive feedback nhất
MATCH (r:EcommerceReview)-[:REVIEWS]->(p:EcommerceProduct)
MATCH (r)-[:ABOUT_DEPARTMENT]->(d:EcommerceDepartment)
RETURN
    r.review_id AS review_id,
    p.clothing_id AS clothing_id,
    d.name AS department,
    r.rating AS rating,
    r.recommended_ind AS recommended,
    r.positive_feedback_count AS positive_feedback_count,
    left(r.review_text, 250) AS review_preview
ORDER BY positive_feedback_count DESC
LIMIT 30;


// 8) Tìm review bằng từ khóa đơn giản
// Ví dụ: "dress"
MATCH (r:EcommerceReview)-[:ABOUT_DEPARTMENT]->(d:EcommerceDepartment)
WHERE toLower(r.combined_text) CONTAINS 'dress'
RETURN
    r.review_id,
    d.name AS department,
    r.rating,
    r.recommended_ind,
    left(r.combined_text, 250) AS text_preview
LIMIT 50;


// 9) Kiểm tra lớp Trend — class thiểu số của target
MATCH (r:EcommerceReview)-[:ABOUT_DEPARTMENT]->(d:EcommerceDepartment)
WHERE d.name = 'Trend'
RETURN
    count(r) AS trend_reviews,
    round(avg(r.rating), 3) AS avg_rating,
    round(avg(r.recommended_ind), 3) AS recommendation_rate;


// 10) Review được recommend mạnh theo department
MATCH (r:EcommerceReview)-[:ABOUT_DEPARTMENT]->(d:EcommerceDepartment)
WHERE r.recommended_ind = 1
RETURN
    d.name AS department,
    count(r) AS recommended_reviews
ORDER BY recommended_reviews DESC;
