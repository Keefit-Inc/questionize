class CreateErrorLogEntries < ActiveRecord::Migration[8.1]
  def change
    # A learner's private record of one missed question: where it lives in their own book,
    # what they chose and the diagnosis. Never the question's text or image.
    create_table :error_log_entries do |t|
      t.references :user, null: false, foreign_key: true
      t.references :generation_run, null: false, foreign_key: true
      t.references :source_observation, foreign_key: true
      t.string :book
      t.string :page
      t.string :number
      t.string :chosen_label
      t.jsonb :diagnosis, null: false
      t.timestamps
    end
  end
end
