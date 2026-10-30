module Research
  class MemoryCycle < ApplicationRecord
    TERMINAL = %w[adopted held failed rolled_back].freeze
    belongs_to :baseline, class_name: "Research::MemoryVersion"
    belongs_to :candidate, class_name: "Research::MemoryVersion", optional: true
    before_validation(on: :create) { self.public_id ||= SecureRandom.hex(8) }
    validates :status, inclusion: { in: %w[queued generating evaluating activating adopted held failed rolled_back] }

    def finish!(state, attributes = {})
      raise ArgumentError, "A terminal decision is required" unless TERMINAL.include?(state)

      with_lock do
        assign_attributes(attributes.merge(status: state, decided_at: decided_at || Time.current))
        self.ledger_entry = MemoryLedgerExport.build_entry(self) || {} if ledger_entry.blank?
        save!
      end
    end

    def event!(stage, message)
      update!(events: events + [ { "stage" => stage, "message" => message, "at" => Time.current.iso8601 } ])
    end

    def public_data
      { id: public_id, status: status, trigger: trigger, created_at: created_at, decided_at: decided_at,
        source_count: registration["source_count"] || observation_ids.size, sampled_sources: observation_ids.size, baseline: baseline.public_data, candidate: candidate&.public_data,
        registration: registration.slice("dataset_hash", "n_items", "repeats", "protocol", "protocol_version", "validation_hash", "training_hash", "worker_source_hash", "model", "source_revision"),
        evaluation: evaluation.except("proofs"), decision_reasons: decision_reasons,
        service_verification: service_verification, events: events }
    end
  end
end
