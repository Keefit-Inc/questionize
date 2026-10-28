# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[8.1].define(version: 2026_10_28_000003) do
  # These are extensions that must be enabled in order to support this database
  enable_extension "pg_catalog.plpgsql"

  create_table "attempts", force: :cascade do |t|
    t.bigint "user_id", null: false
    t.bigint "item_id", null: false
    t.bigint "item_version_id", null: false
    t.string "chosen_label", null: false
    t.boolean "correct", null: false
    t.integer "time_ms"
    t.boolean "rated", default: false, null: false
    t.string "skill", null: false
    t.float "user_rating_before"
    t.float "user_rating_after"
    t.float "item_rating_before"
    t.float "item_rating_after"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["item_id"], name: "index_attempts_on_item_id"
    t.index ["item_version_id"], name: "index_attempts_on_item_version_id"
    t.index ["user_id", "item_id"], name: "index_attempts_one_rated_per_user_item", unique: true, where: "rated"
    t.index ["user_id"], name: "index_attempts_on_user_id"
  end

  create_table "blueprint_versions", force: :cascade do |t|
    t.bigint "blueprint_id", null: false
    t.integer "version", null: false
    t.integer "level_min", null: false
    t.integer "level_max", null: false
    t.jsonb "spec", null: false
    t.text "change_note"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["blueprint_id", "version"], name: "index_blueprint_versions_on_blueprint_id_and_version", unique: true
    t.index ["blueprint_id"], name: "index_blueprint_versions_on_blueprint_id"
  end

  create_table "blueprints", force: :cascade do |t|
    t.string "key", null: false
    t.bigint "competency_id"
    t.bigint "current_version_id"
    t.string "status", default: "hypothesis", null: false
    t.float "confidence", default: 0.5, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["competency_id"], name: "index_blueprints_on_competency_id"
    t.index ["key"], name: "index_blueprints_on_key", unique: true
  end

  create_table "choice_tallies", force: :cascade do |t|
    t.bigint "item_version_id", null: false
    t.string "label", null: false
    t.integer "count", default: 0, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["item_version_id", "label"], name: "index_choice_tallies_on_item_version_id_and_label", unique: true
    t.index ["item_version_id"], name: "index_choice_tallies_on_item_version_id"
  end

  create_table "competencies", force: :cascade do |t|
    t.string "key", null: false
    t.string "subject", null: false
    t.string "strand", null: false
    t.string "name", null: false
    t.text "description"
    t.integer "level_min", null: false
    t.integer "level_max", null: false
    t.string "cognitive_process"
    t.string "knowledge_type"
    t.jsonb "can_do", default: {}, null: false
    t.jsonb "framework_mappings", default: [], null: false
    t.string "status", default: "hypothesis", null: false
    t.float "confidence", default: 0.5, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["key"], name: "index_competencies_on_key", unique: true
  end

  create_table "competency_edges", force: :cascade do |t|
    t.bigint "competency_id", null: false
    t.bigint "prerequisite_id", null: false
    t.string "kind", default: "required", null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["competency_id", "prerequisite_id"], name: "index_competency_edges_on_competency_id_and_prerequisite_id", unique: true
    t.index ["competency_id"], name: "index_competency_edges_on_competency_id"
    t.index ["prerequisite_id"], name: "index_competency_edges_on_prerequisite_id"
  end

  create_table "competency_misconceptions", force: :cascade do |t|
    t.bigint "competency_id", null: false
    t.bigint "misconception_id", null: false
    t.index ["competency_id", "misconception_id"], name: "index_competency_misconceptions_unique", unique: true
    t.index ["competency_id"], name: "index_competency_misconceptions_on_competency_id"
    t.index ["misconception_id"], name: "index_competency_misconceptions_on_misconception_id"
  end

  create_table "evidence_snapshots", force: :cascade do |t|
    t.string "subject_type", null: false
    t.bigint "subject_id", null: false
    t.integer "sample_size", null: false
    t.jsonb "metrics", null: false
    t.datetime "computed_at", null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["subject_type", "subject_id"], name: "index_evidence_snapshots_on_subject"
  end

  create_table "generation_runs", force: :cascade do |t|
    t.bigint "user_id"
    t.bigint "source_id"
    t.jsonb "params", default: {}, null: false
    t.string "status", default: "queued", null: false
    t.jsonb "events", default: [], null: false
    t.jsonb "token_usage", default: {}, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["source_id"], name: "index_generation_runs_on_source_id"
    t.index ["user_id"], name: "index_generation_runs_on_user_id"
  end

  create_table "item_versions", force: :cascade do |t|
    t.bigint "item_id", null: false
    t.integer "version", null: false
    t.bigint "parent_version_id"
    t.text "passage", null: false
    t.text "stem", null: false
    t.jsonb "choices", null: false
    t.string "correct_label", null: false
    t.text "explanation", null: false
    t.jsonb "rationales", null: false
    t.string "skill"
    t.string "source_anchor"
    t.jsonb "verification", default: {}, null: false
    t.string "author_kind", default: "agent", null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.bigint "blueprint_version_id"
    t.index ["blueprint_version_id"], name: "index_item_versions_on_blueprint_version_id"
    t.index ["item_id", "version"], name: "index_item_versions_on_item_id_and_version", unique: true
    t.index ["item_id"], name: "index_item_versions_on_item_id"
    t.index ["parent_version_id"], name: "index_item_versions_on_parent_version_id"
  end

  create_table "items", force: :cascade do |t|
    t.string "public_id", null: false
    t.bigint "source_id"
    t.bigint "generation_run_id"
    t.string "family", null: false
    t.string "subtype", null: false
    t.string "status", default: "verified", null: false
    t.string "visibility", default: "private", null: false
    t.string "origin", default: "generated", null: false
    t.string "content_flags", default: [], null: false, array: true
    t.bigint "current_version_id"
    t.float "rating", default: 1500.0, null: false
    t.integer "attempts_count", default: 0, null: false
    t.integer "correct_count", default: 0, null: false
    t.datetime "published_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["generation_run_id"], name: "index_items_on_generation_run_id"
    t.index ["public_id"], name: "index_items_on_public_id", unique: true
    t.index ["source_id"], name: "index_items_on_source_id"
    t.index ["visibility", "family", "published_at"], name: "index_items_on_visibility_and_family_and_published_at"
  end

  create_table "judge_measurements", force: :cascade do |t|
    t.bigint "item_version_id", null: false
    t.string "label", null: false
    t.string "measure", null: false
    t.float "value", null: false
    t.float "ci_low"
    t.float "ci_high"
    t.string "judge_version", null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["item_version_id", "label", "measure", "judge_version"], name: "index_judge_measurements_unique", unique: true
    t.index ["item_version_id"], name: "index_judge_measurements_on_item_version_id"
  end

  create_table "misconceptions", force: :cascade do |t|
    t.string "key", null: false
    t.string "name", null: false
    t.text "statement", null: false
    t.string "mechanism_family", null: false
    t.string "mechanism_type", null: false
    t.string "scope", default: "domain_specific", null: false
    t.jsonb "level_window", default: {}, null: false
    t.jsonb "diagnostic_signals", default: [], null: false
    t.jsonb "contrasts", default: [], null: false
    t.string "status", default: "hypothesis", null: false
    t.float "confidence", default: 0.5, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["key"], name: "index_misconceptions_on_key", unique: true
  end

  create_table "node_status_events", force: :cascade do |t|
    t.string "node_type", null: false
    t.bigint "node_id", null: false
    t.string "from_status"
    t.string "to_status", null: false
    t.text "reason", null: false
    t.jsonb "evidence", default: {}, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["node_type", "node_id"], name: "index_node_status_events_on_node"
  end

  create_table "skill_ratings", force: :cascade do |t|
    t.bigint "user_id", null: false
    t.string "skill", null: false
    t.float "rating", default: 1500.0, null: false
    t.integer "attempts", default: 0, null: false
    t.integer "correct", default: 0, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["skill", "rating"], name: "index_skill_ratings_on_skill_and_rating"
    t.index ["user_id", "skill"], name: "index_skill_ratings_on_user_id_and_skill", unique: true
    t.index ["user_id"], name: "index_skill_ratings_on_user_id"
  end

  create_table "source_observations", force: :cascade do |t|
    t.string "source_kind", null: false
    t.string "source_ref", null: false
    t.string "language"
    t.string "region"
    t.string "stated_level"
    t.jsonb "observed", null: false
    t.string "extractor", null: false
    t.jsonb "confidence", default: {}, null: false
    t.jsonb "leak_checks", default: {}, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["source_ref"], name: "index_source_observations_on_source_ref"
  end

  create_table "sources", force: :cascade do |t|
    t.string "canonical_url", null: false
    t.string "title"
    t.string "domain"
    t.string "content_hash"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["canonical_url"], name: "index_sources_on_canonical_url", unique: true
  end

  create_table "trap_pattern_targets", force: :cascade do |t|
    t.bigint "trap_pattern_id", null: false
    t.bigint "misconception_id", null: false
    t.index ["misconception_id"], name: "index_trap_pattern_targets_on_misconception_id"
    t.index ["trap_pattern_id", "misconception_id"], name: "idx_on_trap_pattern_id_misconception_id_77cdec6ea0", unique: true
    t.index ["trap_pattern_id"], name: "index_trap_pattern_targets_on_trap_pattern_id"
  end

  create_table "trap_patterns", force: :cascade do |t|
    t.string "key", null: false
    t.string "name", null: false
    t.string "trap_type", null: false
    t.text "construction_rule", null: false
    t.jsonb "attractiveness_drivers", default: [], null: false
    t.text "fairness_guard"
    t.jsonb "judge_signature", default: {}, null: false
    t.string "status", default: "hypothesis", null: false
    t.float "confidence", default: 0.5, null: false
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["key"], name: "index_trap_patterns_on_key", unique: true
  end

  create_table "users", force: :cascade do |t|
    t.string "handle", null: false
    t.string "email"
    t.boolean "anonymous", default: true, null: false
    t.integer "xp", default: 0, null: false
    t.string "api_token", null: false
    t.string "country_code"
    t.datetime "age_confirmed_at"
    t.datetime "created_at", null: false
    t.datetime "updated_at", null: false
    t.index ["api_token"], name: "index_users_on_api_token", unique: true
    t.index ["email"], name: "index_users_on_email", unique: true, where: "(email IS NOT NULL)"
    t.index ["handle"], name: "index_users_on_handle", unique: true
  end

  add_foreign_key "attempts", "item_versions"
  add_foreign_key "attempts", "items"
  add_foreign_key "attempts", "users"
  add_foreign_key "blueprint_versions", "blueprints"
  add_foreign_key "blueprints", "blueprint_versions", column: "current_version_id"
  add_foreign_key "blueprints", "competencies"
  add_foreign_key "choice_tallies", "item_versions"
  add_foreign_key "competency_edges", "competencies"
  add_foreign_key "competency_edges", "competencies", column: "prerequisite_id"
  add_foreign_key "competency_misconceptions", "competencies"
  add_foreign_key "competency_misconceptions", "misconceptions"
  add_foreign_key "generation_runs", "sources"
  add_foreign_key "generation_runs", "users"
  add_foreign_key "item_versions", "blueprint_versions"
  add_foreign_key "item_versions", "item_versions", column: "parent_version_id"
  add_foreign_key "item_versions", "items"
  add_foreign_key "items", "generation_runs"
  add_foreign_key "items", "item_versions", column: "current_version_id"
  add_foreign_key "items", "sources"
  add_foreign_key "judge_measurements", "item_versions"
  add_foreign_key "skill_ratings", "users"
  add_foreign_key "trap_pattern_targets", "misconceptions"
  add_foreign_key "trap_pattern_targets", "trap_patterns"
end
