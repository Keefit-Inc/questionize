class CreateUploadLearning < ActiveRecord::Migration[8.1]
  def change
    create_table :research_memory_versions do |t|
      t.string :public_id, null: false
      t.integer :version, null: false
      t.references :parent, foreign_key: { to_table: :research_memory_versions }
      t.string :content_hash, null: false
      t.text :payload_ciphertext, null: false
      t.jsonb :provenance, null: false, default: {}
      t.timestamps
    end
    add_index :research_memory_versions, :public_id, unique: true
    add_index :research_memory_versions, :version, unique: true
    create_table :research_memory_releases do |t|
      t.references :memory_version, null: false, foreign_key: { to_table: :research_memory_versions }
      t.integer :generation, null: false, default: 1
      t.bigint :observation_cursor, null: false, default: 0
      t.datetime :activated_at
      t.timestamps
    end
    create_table :research_upload_observations do |t|
      t.string :public_id, null: false
      t.references :generation_run, foreign_key: true
      t.references :memory_version, foreign_key: { to_table: :research_memory_versions }
      t.string :question_fingerprint, null: false
      t.string :reference_status, null: false
      t.string :reference_source, null: false
      t.string :knowledge_origin, null: false
      t.string :subtype, null: false
      t.string :outcome, null: false
      t.jsonb :abstract_evidence, null: false, default: {}
      t.jsonb :measurements, null: false, default: {}
      t.boolean :operator_test, null: false, default: false
      t.timestamps
    end
    add_index :research_upload_observations, :public_id, unique: true
    add_index :research_upload_observations, :generation_run_id, unique: true, name: "index_upload_observation_per_run"
    add_index :research_upload_observations, :question_fingerprint
    create_table :research_memory_cycles do |t|
      t.string :public_id, null: false
      t.references :baseline, null: false, foreign_key: { to_table: :research_memory_versions }
      t.references :candidate, foreign_key: { to_table: :research_memory_versions }
      t.string :status, null: false, default: "queued"
      t.string :trigger, null: false, default: "usage_batch"
      t.jsonb :observation_ids, null: false, default: []
      t.jsonb :registration, null: false, default: {}
      t.jsonb :evaluation, null: false, default: {}
      t.jsonb :decision_reasons, null: false, default: []
      t.jsonb :service_verification, null: false, default: {}
      t.jsonb :events, null: false, default: []
      t.string :lease_digest
      t.datetime :leased_at
      t.datetime :lease_expires_at
      t.datetime :decided_at
      t.timestamps
    end
    add_index :research_memory_cycles, :public_id, unique: true
    add_index :research_memory_cycles, :status, unique: true, where: "status = 'queued'", name: "index_one_queued_memory_cycle"
    create_table :research_worker_credentials do |t|
      t.string :name, null: false
      t.string :token_digest, null: false
      t.datetime :last_seen_at
      t.datetime :revoked_at
      t.timestamps
    end
    add_index :research_worker_credentials, :token_digest, unique: true
  end
end
