class ItemReview < ApplicationRecord
  TRIGGERS = %w[repeated_flags strong_learner_flag crowd_disagreement].freeze
  STATUSES = %w[queued done failed].freeze
  VERDICTS = %w[keep revise retire].freeze

  belongs_to :item
  belongs_to :from_version, class_name: "ItemVersion"
  belongs_to :to_version, class_name: "ItemVersion", optional: true

  validates :trigger, inclusion: { in: TRIGGERS }
  validates :status, inclusion: { in: STATUSES }
  validates :verdict, inclusion: { in: VERDICTS }, allow_nil: true
end
