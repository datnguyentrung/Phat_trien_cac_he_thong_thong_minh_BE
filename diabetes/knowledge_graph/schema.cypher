// Diabetes Knowledge Graph schema
// Neo4j 5.x

CREATE CONSTRAINT respondent_id_unique IF NOT EXISTS
FOR (n:Respondent) REQUIRE n.respondent_id IS UNIQUE;

CREATE CONSTRAINT concept_id_unique IF NOT EXISTS
FOR (n:Concept) REQUIRE n.concept_id IS UNIQUE;

CREATE INDEX concept_feature_idx IF NOT EXISTS
FOR (n:Concept) ON (n.feature);

CREATE INDEX respondent_age_group_idx IF NOT EXISTS
FOR (n:Respondent) ON (n.age_group);

CREATE INDEX respondent_gen_health_idx IF NOT EXISTS
FOR (n:Respondent) ON (n.general_health);
