class AddLevels < ActiveRecord::Migration[8.1]
  def change
    # Who a learner is studying as (grade band or target test), and who an item was written for
    # (docs/LEARNING_MODEL.md §4). Items made before levels existed were written for GMAT/LSAT.
    add_column :users, :level, :string
    add_column :items, :level, :string, null: false, default: "gmat"
    # The kind of situation the item is set in, for its illustration.
    add_column :items, :scene, :string
    add_index :items, %i[level published_at]
  end
end
