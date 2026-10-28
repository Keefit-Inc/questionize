# One Argument Judge measurement for one option of one item version.
class JudgeMeasurement < ApplicationRecord
  MEASURES = %w[support_delta necessity sufficiency scope entailment].freeze

  belongs_to :item_version

  validates :label, inclusion: { in: ItemVersion::LABELS }
  validates :measure, inclusion: { in: MEASURES }
  validates :value, numericality: { greater_than_or_equal_to: -1, less_than_or_equal_to: 1 }
  validates :judge_version, presence: true
end
