class AddMemoryCycleLedger < ActiveRecord::Migration[8.1]
  def change
    add_column :research_memory_cycles, :ledger_entry, :jsonb, null: false, default: {}
  end
end
