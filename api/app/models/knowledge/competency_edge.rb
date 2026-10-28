module Knowledge
  class CompetencyEdge < ApplicationRecord
    KINDS = %w[required helpful].freeze

    belongs_to :competency, class_name: "Knowledge::Competency"
    belongs_to :prerequisite, class_name: "Knowledge::Competency"

    validates :kind, inclusion: { in: KINDS }
    validates :prerequisite_id, uniqueness: { scope: :competency_id }
    validate :not_self

    private

    def not_self
      errors.add(:prerequisite, "cannot be the competency itself") if competency_id == prerequisite_id
    end
  end
end
