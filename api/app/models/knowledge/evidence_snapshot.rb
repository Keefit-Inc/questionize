module Knowledge
  # Aggregated learner evidence about a knowledge node or blueprint version.
  class EvidenceSnapshot < ApplicationRecord
    belongs_to :subject, polymorphic: true

    validates :sample_size, numericality: { greater_than_or_equal_to: 0 }
    validates :metrics, :computed_at, presence: true
  end
end
