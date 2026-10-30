module Research
  class UploadObservation < ApplicationRecord
    belongs_to :generation_run, optional: true
    belongs_to :memory_version, optional: true
    before_validation(on: :create) { self.public_id ||= SecureRandom.hex(8) }
    validates :public_id, :question_fingerprint, :subtype, presence: true
    validates :question_fingerprint, format: { with: /\A[0-9a-f]{64}\z/ }
    validates :reference_source, format: { with: /\A[a-z_]{1,80}\z/ }
    validates :subtype, length: { maximum: 50 }
    validates :reference_status, inclusion: { in: %w[confirmed_reference supplied_reference ai_estimated unconfirmed disputed] }
    validates :knowledge_origin, inclusion: { in: %w[expert_reference user_experience] }
    validates :outcome, inclusion: { in: %w[reference_match reference_mismatch ai_agreement ai_disagreement unresolved] }
    validate :abstract_only
    after_create_commit :schedule_review

    def failure_signal?
      %w[reference_mismatch ai_disagreement].include?(outcome)
    end

    def public_data
      { id: public_id, created_at: created_at, subtype: subtype, reference_status: reference_status,
        reference_source: reference_source, knowledge_origin: knowledge_origin, outcome: outcome,
        memory_version: memory_version&.version, operator_test: operator_test,
        measurements: measurements.slice("main_matches_reference", "control_matches_reference", "models_agree", "main_model", "control_model", "logical_calls", "runtime_version", "memory_hash") }
    end

    private

    def schedule_review
      UploadScheduleJob.request_check
    rescue StandardError => e
      Rails.logger.warn("[UploadLearning] scheduling unavailable: #{e.class.name}")
    end

    def abstract_only
      allowed = %w[failure_kind lesson competency key_rule]
      errors.add(:abstract_evidence, "contains unsupported fields") if abstract_evidence.keys - allowed != []
      errors.add(:abstract_evidence, "fields must be short abstract strings") unless abstract_evidence.values.all? { _1.is_a?(String) && _1.length <= 500 }
      allowed_measures = %w[main_matches_reference control_matches_reference models_agree main_model control_model logical_calls runtime_version memory_hash]
      errors.add(:measurements, "contains unsupported fields") if (measurements.keys - allowed_measures).any?
      measurements.each do |key, value|
        if %w[main_matches_reference control_matches_reference models_agree].include?(key)
          errors.add(:measurements, "requires boolean agreement fields") unless [ true, false, nil ].include?(value)
        elsif key == "logical_calls"
          errors.add(:measurements, "requires a bounded call count") unless value.is_a?(Integer) && value.between?(0, 20)
        else
          errors.add(:measurements, "requires short technical identifiers") unless value.nil? || (value.is_a?(String) && value.match?(/\A[a-zA-Z0-9_.\/:+\-]{1,120}\z/))
        end
      end
    end
  end
end
