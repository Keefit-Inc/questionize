class CreateUserIdentities < ActiveRecord::Migration[8.1]
  def change
    # Sign-in providers linked to a user (Facebook Login first). Only the provider's user id and
    # what the learner agreed to share are kept; the provider's access token is never stored.
    create_table :user_identities do |t|
      t.references :user, null: false, foreign_key: true
      t.string :provider, null: false
      t.string :uid, null: false
      t.string :name
      t.string :email
      t.timestamps
    end
    add_index :user_identities, %i[provider uid], unique: true
  end
end
