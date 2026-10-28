module Knowledge
  class Competency < ApplicationRecord
    include Node

    LEVELS = (1..14)
    COGNITIVE_PROCESSES = %w[remember understand apply analyze evaluate create].freeze
    KNOWLEDGE_TYPES = %w[factual conceptual procedural metacognitive].freeze

    has_many :prerequisite_edges, class_name: "Knowledge::CompetencyEdge", dependent: :destroy
    has_many :prerequisites, through: :prerequisite_edges
    has_many :competency_misconceptions, class_name: "Knowledge::CompetencyMisconception", dependent: :destroy
    has_many :misconceptions, through: :competency_misconceptions
    has_many :blueprints, class_name: "Knowledge::Blueprint", dependent: :nullify

    validates :subject, :strand, :name, presence: true
    validates :level_min, :level_max, inclusion: { in: LEVELS }
    validates :cognitive_process, inclusion: { in: COGNITIVE_PROCESSES }, allow_nil: true
    validates :knowledge_type, inclusion: { in: KNOWLEDGE_TYPES }, allow_nil: true
    validate :level_range_ordered

    private

    def level_range_ordered
      errors.add(:level_max, "must not be below level_min") if level_min && level_max && level_max < level_min
    end
  end
end
