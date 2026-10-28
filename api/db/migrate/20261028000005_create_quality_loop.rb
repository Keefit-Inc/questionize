class CreateQualityLoop < ActiveRecord::Migration[8.1]
  def change
    # Learner signals on a specific item version (docs/ARCHITECTURE.md §5.4).
    create_table :feedbacks do |t|
      t.references :user, null: false, foreign_key: true
      t.references :item_version, null: false, foreign_key: true
      t.string :kind, null: false # up, down, flag
      t.string :reason
      t.text :comment
      t.timestamps
    end
    add_index :feedbacks, [ :user_id, :item_version_id, :kind ], unique: true

    # Every automatic re-review, its trigger and its outcome.
    create_table :item_reviews do |t|
      t.references :item, null: false, foreign_key: true
      t.references :from_version, null: false, foreign_key: { to_table: :item_versions }
      t.references :to_version, foreign_key: { to_table: :item_versions }
      t.string :trigger, null: false
      t.string :status, null: false, default: "queued"
      t.string :verdict
      t.jsonb :findings, null: false, default: []
      t.timestamps
    end
  end
end
