# A sign-in provider account linked to a user (docs/ARCHITECTURE.md §5.7).
class UserIdentity < ApplicationRecord
  PROVIDERS = %w[facebook].freeze

  belongs_to :user

  validates :provider, inclusion: { in: PROVIDERS }
  validates :uid, presence: true, uniqueness: { scope: :provider }
end
