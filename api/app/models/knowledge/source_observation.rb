module Knowledge
  # Abstract fields extracted from one source item. Never holds the source's wording,
  # stimulus, options or images (docs/KNOWLEDGE_MODEL.md §6).
  class SourceObservation < ApplicationRecord
    SOURCE_KINDS = %w[own_item article teacher_contribution print_scan public_domain].freeze

    validates :source_kind, inclusion: { in: SOURCE_KINDS }
    validates :source_ref, :extractor, presence: true
    validates :observed, presence: true
    after_create_commit :check_research_batch

    # Independent sources behind a set of observations, for corroboration.
    def self.independent_source_count
      distinct.count(:source_ref)
    end

    private

    def check_research_batch
      Research::Evidence.request_check if observed["family"] == "CR" && observed["level"] == "gmat"
    end
  end
end
