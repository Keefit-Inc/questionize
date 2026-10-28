class CreateLearningTables < ActiveRecord::Migration[8.1]
  def change
    create_table :users do |t|
      t.string :handle, null: false
      t.string :email
      t.boolean :anonymous, null: false, default: true
      t.integer :xp, null: false, default: 0
      t.string :api_token, null: false
      t.string :country_code
      t.datetime :age_confirmed_at
      t.timestamps
    end
    add_index :users, :handle, unique: true
    add_index :users, :email, unique: true, where: "email IS NOT NULL"
    add_index :users, :api_token, unique: true

    create_table :skill_ratings do |t|
      t.references :user, null: false, foreign_key: true
      # "overall", a family ("CR"), or family:subtype ("CR:assumption")
      t.string :skill, null: false
      t.float :rating, null: false, default: 1500.0
      t.integer :attempts, null: false, default: 0
      t.integer :correct, null: false, default: 0
      t.timestamps
    end
    add_index :skill_ratings, [ :user_id, :skill ], unique: true
    add_index :skill_ratings, [ :skill, :rating ]
  end
end
