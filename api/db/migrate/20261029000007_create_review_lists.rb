class CreateReviewLists < ActiveRecord::Migration[8.1]
  def change
    # A learner's review list: snapped questions (error-log entries) plus bank items they missed
    # or saved. Archived ones are mastered and kept out of the way.
    add_column :error_log_entries, :archived_at, :datetime

    create_table :saved_items do |t|
      t.references :user, null: false, foreign_key: true
      t.references :item, null: false, foreign_key: true
      t.string :reason, null: false # missed | saved
      t.datetime :archived_at
      t.timestamps
    end
    add_index :saved_items, %i[user_id item_id], unique: true
  end
end
