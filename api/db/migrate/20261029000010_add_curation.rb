class AddCuration < ActiveRecord::Migration[8.1]
  def change
    # Curators photograph official-style items with their answer keys to build research datasets
    # and the knowledge model (docs/DECISIONS.md R2, R3; research/README.md).
    add_column :users, :curator, :boolean, null: false, default: false
    # Which private dataset a curated entry belongs to (e.g. "official-cr-v1"). Item text is never
    # stored; the dataset itself lives on the curator's device and in private storage.
    add_column :error_log_entries, :dataset, :string
    add_index :error_log_entries, :dataset
  end
end
