module Research
  class Cycle < ApplicationRecord
    ACTIVE = %w[queued generating evaluating activating].freeze
    TERMINAL = %w[adopted held failed].freeze
    belongs_to :release
    belongs_to :benchmark
    belongs_to :baseline_policy, class_name: "Research::PolicyVersion"
    belongs_to :candidate_policy, class_name: "Research::PolicyVersion", optional: true
    belongs_to :requested_by, class_name: "User", optional: true
    has_many :events, class_name: "Research::CycleEvent", dependent: :destroy
    validates :status, inclusion: { in: ACTIVE + TERMINAL }
    validates :trigger, inclusion: { in: %w[operator_research usage_batch] }
    validates :public_id, presence: true, uniqueness: true
    before_validation -> { self.public_id ||= SecureRandom.hex(8) }, on: :create
    scope :in_progress, -> { where(status: ACTIVE) }

    def event!(stage, message, data = {})
      events.create!(stage: stage, message: message, data: data)
      touch
    end

    def public_data
      comparison = evaluation["comparison"].to_h.slice("gained", "lost", "delta", "mcnemar_p", "diff_ci95", "standard_changes", "standard_regressions", "except_gained")
      result = evaluation.present? ? {
        baseline: evaluation["baseline"].to_h.slice("n", "correct", "accuracy", "ci95"),
        candidate: evaluation["candidate"].to_h.slice("n", "correct", "accuracy", "ci95"),
        comparison: comparison, gate: evaluation["gate"].to_h.slice("passed", "reasons"),
        evaluation_kind: evaluation["evaluation_kind"], evaluator_version: evaluation["evaluator_version"], evaluator_hash: evaluation["evaluator_hash"]
      } : nil
      {
        id: public_id, status: status, trigger: trigger, created_at: created_at, updated_at: updated_at,
        baseline_policy: baseline_policy.public_data, candidate_policy: candidate_policy&.public_data,
        benchmark: benchmark.public_data, proposal: proposal.presence, evaluation: result,
        criteria: criteria, decision_reasons: decision_reasons, service_verification: service_verification.presence,
        sources: source_snapshot.slice("trusted_sources", "new_rated_attempts"), code_revision: code_revision,
        events: events.order(:id).map do |event|
          { stage: event.stage, message: event.message, created_at: event.created_at,
            data: event.data.slice("policy_id", "policy_hash", "baseline_policy_id", "baseline_policy_hash", "benchmark_hash", "n", "correct", "delta", "reason", "generation", "model", "trigger") }
        end
      }
    end
  end
end
