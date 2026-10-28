class CreateBankTables < ActiveRecord::Migration[8.1]
  def change
    create_table :sources do |t|
      t.string :canonical_url, null: false
      t.string :title
      t.string :domain
      t.string :content_hash
      t.timestamps
    end
    add_index :sources, :canonical_url, unique: true

    create_table :generation_runs do |t|
      t.references :user, foreign_key: true
      t.references :source, foreign_key: true
      t.jsonb :params, null: false, default: {}
      t.string :status, null: false, default: "queued"
      t.jsonb :events, null: false, default: []
      t.jsonb :token_usage, null: false, default: {}
      t.timestamps
    end

    create_table :items do |t|
      t.string :public_id, null: false
      t.references :source, foreign_key: true
      t.references :generation_run, foreign_key: true
      t.string :family, null: false
      t.string :subtype, null: false
      t.string :status, null: false, default: "verified"
      t.string :visibility, null: false, default: "private"
      t.string :origin, null: false, default: "generated"
      t.string :content_flags, array: true, null: false, default: []
      t.bigint :current_version_id
      t.float :rating, null: false, default: 1500.0
      t.integer :attempts_count, null: false, default: 0
      t.integer :correct_count, null: false, default: 0
      t.datetime :published_at
      t.timestamps
    end
    add_index :items, :public_id, unique: true
    add_index :items, [ :visibility, :family, :published_at ]

    create_table :item_versions do |t|
      t.references :item, null: false, foreign_key: true
      t.integer :version, null: false
      t.references :parent_version, foreign_key: { to_table: :item_versions }
      t.text :passage, null: false
      t.text :stem, null: false
      t.jsonb :choices, null: false
      t.string :correct_label, null: false
      t.text :explanation, null: false
      # [{label, rationale, trap, misconception_key}]
      t.jsonb :rationales, null: false
      t.string :skill
      t.string :source_anchor
      t.jsonb :verification, null: false, default: {}
      t.string :author_kind, null: false, default: "agent"
      t.timestamps
    end
    add_index :item_versions, [ :item_id, :version ], unique: true
    add_foreign_key :items, :item_versions, column: :current_version_id

    create_table :attempts do |t|
      t.references :user, null: false, foreign_key: true
      t.references :item, null: false, foreign_key: true
      t.references :item_version, null: false, foreign_key: true
      t.string :chosen_label, null: false
      t.boolean :correct, null: false
      t.integer :time_ms
      t.boolean :rated, null: false, default: false
      t.string :skill, null: false
      t.float :user_rating_before
      t.float :user_rating_after
      t.float :item_rating_before
      t.float :item_rating_after
      t.timestamps
    end
    # Only a user's first attempt on an item is rated.
    add_index :attempts, [ :user_id, :item_id ], unique: true, where: "rated", name: "index_attempts_one_rated_per_user_item"

    create_table :choice_tallies do |t|
      t.references :item_version, null: false, foreign_key: true
      t.string :label, null: false
      t.integer :count, null: false, default: 0
      t.timestamps
    end
    add_index :choice_tallies, [ :item_version_id, :label ], unique: true
  end
end
