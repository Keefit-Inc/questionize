class SeparateKnowledgeEvidenceOrigins < ActiveRecord::Migration[8.1]
  def change
    add_column :source_observations, :knowledge_origin, :string, null: false, default: "legacy_unclassified"
    add_column :source_observations, :evidence_status, :string, null: false, default: "unconfirmed"
    add_column :source_observations, :rights_scope, :string, null: false, default: "private_research"
    add_column :source_observations, :provenance, :jsonb, null: false, default: {}
    add_index :source_observations, [ :knowledge_origin, :evidence_status ]
  end
end
