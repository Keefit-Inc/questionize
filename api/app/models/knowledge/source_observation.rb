module Knowledge
  # Abstract fields extracted from one source item. Never holds the source's wording,
  # stimulus, options or images (docs/KNOWLEDGE_MODEL.md §6).
  class SourceObservation < ApplicationRecord
    SOURCE_KINDS = %w[own_item article teacher_contribution print_scan public_domain].freeze
    ORIGINS = %w[expert_reference user_experience original_authored legacy_unclassified].freeze
    EVIDENCE_STATUSES = %w[confirmed ai_estimated unconfirmed].freeze
    RIGHTS_SCOPES = %w[private_research shared_abstract].freeze

    validates :source_kind, inclusion: { in: SOURCE_KINDS }
    validates :source_ref, :extractor, presence: true
    validates :observed, presence: true
    validates :knowledge_origin, inclusion: { in: ORIGINS }
    validates :evidence_status, inclusion: { in: EVIDENCE_STATUSES }
    validates :rights_scope, inclusion: { in: RIGHTS_SCOPES }
    validate :protect_expert_reference
    after_create_commit :check_research_batch

    # Callers must choose a namespace. AI agreement never promotes a usage-derived
    # observation to expert-reference evidence or to a confirmed training target.
    def self.memory_candidates(origin:)
      raise ArgumentError, "Choose an explicit knowledge origin" unless ORIGINS.include?(origin)

      where(knowledge_origin: origin, evidence_status: "confirmed")
    end

    # Independent sources behind a set of observations, for corroboration.
    def self.independent_source_count
      distinct.count(:source_ref)
    end

    private

    def protect_expert_reference
      return unless knowledge_origin == "expert_reference"

      errors.add(:rights_scope, "expert references must remain private") unless rights_scope == "private_research"
      errors.add(:provenance, "requires source digest and derivation") unless provenance["source_digest"].present? && provenance["derivation"].present?
    end

    def check_research_batch
      Research::Evidence.request_check if observed["family"] == "CR" && observed["level"] == "gmat"
    end
  end
end
