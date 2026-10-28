class AddMaps < ActiveRecord::Migration[8.1]
  def change
    # "questions" runs produce items; "map" runs produce an argument map in `result`.
    add_column :generation_runs, :kind, :string, null: false, default: "questions"
    add_column :generation_runs, :result, :jsonb
    add_index :generation_runs, [ :source_id, :kind, :status ]

    # A reader's answer to a map challenge, given before the judged answer is revealed.
    create_table :challenge_answers do |t|
      t.references :user, null: false, foreign_key: true
      t.references :generation_run, null: false, foreign_key: true
      t.integer :challenge_index, null: false
      t.string :choice, null: false
      t.timestamps
    end
    add_index :challenge_answers, [ :user_id, :generation_run_id, :challenge_index ], unique: true, name: "index_challenge_answers_one_per_user"
  end
end
