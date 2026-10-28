class Feedback < ApplicationRecord
  KINDS = %w[up down flag].freeze
  REASONS = %w[wrong_key two_answers unclear typo offensive other].freeze

  belongs_to :user
  belongs_to :item_version

  validates :kind, inclusion: { in: KINDS }
  validates :reason, inclusion: { in: REASONS }, if: -> { kind == "flag" }
  validates :kind, uniqueness: { scope: %i[user_id item_version_id] }
  validates :comment, length: { maximum: 1000 }
end
