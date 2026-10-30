class CreateResearchEvolution < ActiveRecord::Migration[8.1]
  def change
    add_column :item_reviews, :capability_policy, :jsonb
    add_column :item_reviews, :policy_pinned, :boolean, null: false, default: false

    create_table :research_policy_versions do |t|
      t.string :public_id, null: false
      t.string :subject, null: false, default: "CR"
      t.string :level, null: false, default: "gmat"
      t.string :capability, null: false, default: "C3.1"
      t.string :kind, null: false, default: "judge_operator"
      t.integer :version, null: false
      t.jsonb :payload, null: false
      t.string :content_hash, null: false
      t.jsonb :provenance, null: false, default: {}
      t.timestamps
    end
    add_index :research_policy_versions, :public_id, unique: true
    add_index :research_policy_versions, %i[subject level capability version], unique: true, name: "index_research_policy_version_scope"

    create_table :research_benchmarks do |t|
      t.string :public_id, null: false
      t.string :name, null: false
      t.string :subject, null: false, default: "CR"
      t.string :level, null: false, default: "gmat"
      t.string :kind, null: false, default: "decision_replay"
      t.string :purpose, null: false, default: "development_regression"
      t.string :content_hash, null: false
      t.jsonb :cases, null: false, default: []
      t.jsonb :provenance, null: false, default: {}
      t.boolean :enabled, null: false, default: false
      t.timestamps
    end
    add_index :research_benchmarks, :public_id, unique: true
    add_index :research_benchmarks, :content_hash, unique: true

    create_table :research_releases do |t|
      t.string :subject, null: false, default: "CR"
      t.string :level, null: false, default: "gmat"
      t.string :capability, null: false, default: "C3.1"
      t.references :policy_version, null: false, foreign_key: { to_table: :research_policy_versions }
      t.integer :generation, null: false, default: 1
      t.bigint :source_cursor, null: false, default: 0
      t.bigint :attempt_cursor, null: false, default: 0
      t.datetime :last_automatic_at
      t.datetime :activated_at
      t.timestamps
    end
    add_index :research_releases, %i[subject level capability], unique: true

    create_table :research_cycles do |t|
      t.string :public_id, null: false
      t.references :release, null: false, foreign_key: { to_table: :research_releases }
      t.references :benchmark, null: false, foreign_key: { to_table: :research_benchmarks }
      t.references :baseline_policy, null: false, foreign_key: { to_table: :research_policy_versions }
      t.references :candidate_policy, foreign_key: { to_table: :research_policy_versions }
      t.references :requested_by, foreign_key: { to_table: :users }
      t.string :status, null: false, default: "queued"
      t.string :trigger, null: false
      t.string :code_revision, null: false
      t.jsonb :source_snapshot, null: false, default: {}
      t.jsonb :criteria, null: false, default: {}
      t.jsonb :proposal, null: false, default: {}
      t.jsonb :evaluation, null: false, default: {}
      t.jsonb :decision_reasons, null: false, default: []
      t.jsonb :service_verification, null: false, default: {}
      t.jsonb :ledger_entry, null: false, default: {}
      t.datetime :decided_at
      t.datetime :activated_at
      t.timestamps
    end
    add_index :research_cycles, :public_id, unique: true
    add_index :research_cycles, :release_id, unique: true,
      where: "status IN ('queued', 'generating', 'evaluating', 'activating')", name: "index_one_running_research_cycle"

    create_table :research_cycle_events do |t|
      t.references :cycle, null: false, foreign_key: { to_table: :research_cycles }
      t.string :stage, null: false
      t.string :message, null: false
      t.jsonb :data, null: false, default: {}
      t.datetime :created_at, null: false
    end
  end
end
