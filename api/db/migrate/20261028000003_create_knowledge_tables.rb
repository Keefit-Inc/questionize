# Knowledge model (docs/KNOWLEDGE_MODEL.md). Every node carries a status and confidence
# and is published openly; nothing here references an individual learner.
class CreateKnowledgeTables < ActiveRecord::Migration[8.1]
  def change
    create_table :competencies do |t|
      t.string :key, null: false
      t.string :subject, null: false
      t.string :strand, null: false
      t.string :name, null: false
      t.text :description
      t.integer :level_min, null: false
      t.integer :level_max, null: false
      t.string :cognitive_process
      t.string :knowledge_type
      t.jsonb :can_do, null: false, default: {}
      t.jsonb :framework_mappings, null: false, default: []
      t.string :status, null: false, default: "hypothesis"
      t.float :confidence, null: false, default: 0.5
      t.timestamps
    end
    add_index :competencies, :key, unique: true

    create_table :competency_edges do |t|
      t.references :competency, null: false, foreign_key: true
      t.references :prerequisite, null: false, foreign_key: { to_table: :competencies }
      t.string :kind, null: false, default: "required"
      t.timestamps
    end
    add_index :competency_edges, [ :competency_id, :prerequisite_id ], unique: true

    create_table :misconceptions do |t|
      t.string :key, null: false
      t.string :name, null: false
      t.text :statement, null: false
      t.string :mechanism_family, null: false
      t.string :mechanism_type, null: false
      t.string :scope, null: false, default: "domain_specific"
      t.jsonb :level_window, null: false, default: {}
      t.jsonb :diagnostic_signals, null: false, default: []
      t.jsonb :contrasts, null: false, default: []
      t.string :status, null: false, default: "hypothesis"
      t.float :confidence, null: false, default: 0.5
      t.timestamps
    end
    add_index :misconceptions, :key, unique: true

    create_table :competency_misconceptions do |t|
      t.references :competency, null: false, foreign_key: true
      t.references :misconception, null: false, foreign_key: true
    end
    add_index :competency_misconceptions, [ :competency_id, :misconception_id ], unique: true, name: "index_competency_misconceptions_unique"

    create_table :trap_patterns do |t|
      t.string :key, null: false
      t.string :name, null: false
      t.string :trap_type, null: false
      t.text :construction_rule, null: false
      t.jsonb :attractiveness_drivers, null: false, default: []
      t.text :fairness_guard
      # Expected Argument Judge measurements for options built this way, e.g.
      # {"support_delta": [0.2, 0.5], "necessity": [0.0, 0.3]}
      t.jsonb :judge_signature, null: false, default: {}
      t.string :status, null: false, default: "hypothesis"
      t.float :confidence, null: false, default: 0.5
      t.timestamps
    end
    add_index :trap_patterns, :key, unique: true

    create_table :trap_pattern_targets do |t|
      t.references :trap_pattern, null: false, foreign_key: true
      t.references :misconception, null: false, foreign_key: true
    end
    add_index :trap_pattern_targets, [ :trap_pattern_id, :misconception_id ], unique: true

    create_table :blueprints do |t|
      t.string :key, null: false
      t.references :competency, foreign_key: true
      t.bigint :current_version_id
      t.string :status, null: false, default: "hypothesis"
      t.float :confidence, null: false, default: 0.5
      t.timestamps
    end
    add_index :blueprints, :key, unique: true

    create_table :blueprint_versions do |t|
      t.references :blueprint, null: false, foreign_key: true
      t.integer :version, null: false
      t.integer :level_min, null: false
      t.integer :level_max, null: false
      # objective, stimulus_spec, stem_patterns, key_rule, distractor_slots,
      # difficulty_drivers, ambiguity_risks, variation_axes, teaching_notes
      t.jsonb :spec, null: false
      t.text :change_note
      t.timestamps
    end
    add_index :blueprint_versions, [ :blueprint_id, :version ], unique: true
    add_foreign_key :blueprints, :blueprint_versions, column: :current_version_id

    add_reference :item_versions, :blueprint_version, foreign_key: true

    create_table :source_observations do |t|
      t.string :source_kind, null: false
      # Keyed hash of the bibliographic identifier and position; never published.
      t.string :source_ref, null: false
      t.string :language
      t.string :region
      t.string :stated_level
      t.jsonb :observed, null: false
      t.string :extractor, null: false
      t.jsonb :confidence, null: false, default: {}
      t.jsonb :leak_checks, null: false, default: {}
      t.timestamps
    end
    add_index :source_observations, :source_ref

    create_table :node_status_events do |t|
      t.references :node, polymorphic: true, null: false
      t.string :from_status
      t.string :to_status, null: false
      t.text :reason, null: false
      t.jsonb :evidence, null: false, default: {}
      t.timestamps
    end

    create_table :evidence_snapshots do |t|
      t.references :subject, polymorphic: true, null: false
      t.integer :sample_size, null: false
      # e.g. selection rate by rating band, discrimination, prevalence by level
      t.jsonb :metrics, null: false
      t.datetime :computed_at, null: false
      t.timestamps
    end

    # Argument Judge output per item option (docs/ARCHITECTURE.md §4.5).
    create_table :judge_measurements do |t|
      t.references :item_version, null: false, foreign_key: true
      t.string :label, null: false
      t.string :measure, null: false
      t.float :value, null: false
      t.float :ci_low
      t.float :ci_high
      t.string :judge_version, null: false
      t.timestamps
    end
    add_index :judge_measurements, [ :item_version_id, :label, :measure, :judge_version ], unique: true, name: "index_judge_measurements_unique"
  end
end
