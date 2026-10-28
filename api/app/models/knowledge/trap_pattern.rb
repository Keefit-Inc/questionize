module Knowledge
  class TrapPattern < ApplicationRecord
    include Node

    # Item-level option tags produced by the AI service.
    TRAP_TYPES = %w[out_of_scope too_extreme reversal half_right unsupported irrelevant distortion grammar_error changes_meaning].freeze

    has_many :trap_pattern_targets, class_name: "Knowledge::TrapPatternTarget", dependent: :destroy
    has_many :misconceptions, through: :trap_pattern_targets

    validates :name, :construction_rule, presence: true
    validates :trap_type, inclusion: { in: TRAP_TYPES }
  end
end
