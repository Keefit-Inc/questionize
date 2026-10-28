module Knowledge
  class Misconception < ApplicationRecord
    include Node

    # Two-level mechanism taxonomy (docs/KNOWLEDGE_MODEL.md §3.4).
    MECHANISM_FAMILIES = %w[knowledge generalization attention logic scope_language processing metacognitive].freeze
    SCOPES = %w[domain_specific domain_general].freeze

    has_many :competency_misconceptions, class_name: "Knowledge::CompetencyMisconception", dependent: :destroy
    has_many :competencies, through: :competency_misconceptions
    has_many :trap_pattern_targets, class_name: "Knowledge::TrapPatternTarget", dependent: :destroy
    has_many :trap_patterns, through: :trap_pattern_targets

    validates :name, :statement, :mechanism_type, presence: true
    validates :mechanism_family, inclusion: { in: MECHANISM_FAMILIES }
    validates :scope, inclusion: { in: SCOPES }
  end
end
