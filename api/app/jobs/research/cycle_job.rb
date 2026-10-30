module Research
  class CycleJob < ApplicationJob
    queue_as :default
    class_attribute :ai_client_factory, default: -> { AiService::Client.new(read_timeout: 90) }

    def perform(cycle_id)
      @cycle = Cycle.find(cycle_id)
      claimed = false
      @cycle.with_lock do
        if @cycle.status == "queued"
          @cycle.update!(status: "generating")
          @cycle.event!("generating", "Meta is proposing one bounded policy from aggregate evidence.")
          claimed = true
        end
      end
      return unless claimed

      @client = ai_client_factory.call
      proposal = @client.propose_policy(
        "subject" => "CR", "level" => "gmat", "baseline" => @cycle.baseline_policy.payload,
        "observations" => proposer_observations
      )
      save_candidate(proposal)
      @cycle.update!(status: "evaluating")
      @cycle.event!("evaluating", "Both policies replay the same frozen decisions; no new solver calls are made.",
        "benchmark_hash" => @cycle.benchmark.content_hash, "n" => @cycle.benchmark.cases.size)
      result = @client.evaluate_policy(
        "baseline" => @cycle.baseline_policy.context, "candidate" => @cycle.candidate_policy.context,
        "benchmark" => @cycle.benchmark.context, "criteria" => @cycle.criteria.slice("min_cases", "min_improvements", "max_regressions")
      )
      @cycle.update!(evaluation: result)
      reasons = DecisionGate.reasons(@cycle, result)
      return finish!("held", reasons) if reasons.any?

      activate!
    rescue StandardError => e
      raise if @cycle.nil?

      restore_baseline!
      @cycle.update!(service_verification: { "verified" => false, "failure" => e.class.name, "checked_at" => Time.current.iso8601 })
      finish!("failed", [ "The cycle stopped before verified service application (#{e.class.name}). The prior release was retained or restored." ])
      Rails.logger.error("[Research::CycleJob] #{@cycle.public_id}: #{e.class.name}")
    end

    private

    def proposer_observations
      cases = @cycle.benchmark.cases
      {
        "trusted_sources" => @cycle.source_snapshot["trusted_sources"],
        "rated_attempts" => @cycle.source_snapshot["new_rated_attempts"],
        "recorded_cases" => cases.size,
        "except_cases" => cases.count { _1["operator"] == "except" },
        "except_wrong_overrides" => cases.count { _1["operator"] == "except" && _1["solver_answer"] == _1["key"] && _1["baseline_answer"] != _1["key"] },
        "standard_cases" => cases.count { _1["operator"] == "standard" }
      }
    end

    def save_candidate(proposal)
      @cycle.release.with_lock do
        version = PolicyVersion.where(subject: "CR", level: "gmat", capability: "C3.1").maximum(:version).to_i + 1
        candidate = PolicyVersion.create!(version: version, payload: proposal.fetch("payload"),
          provenance: { "cycle_id" => @cycle.public_id, "generator_model" => proposal["model"],
                        "source_observation_ids" => @cycle.source_snapshot["source_observation_ids"] })
        @cycle.update!(candidate_policy: candidate, proposal: proposal.slice("reason", "hypothesis", "model", "generator_version", "prompt_hash", "logical_calls", "duration_seconds"))
      end
      @cycle.event!("candidate", "The candidate is an immutable version, not executable model-generated code.",
        "policy_id" => @cycle.candidate_policy.public_id, "policy_hash" => @cycle.candidate_policy.content_hash,
        "model" => @cycle.proposal["model"])
    end

    def activate!
      @cycle.update!(status: "activating")
      @cycle.event!("gate_passed", "The candidate improved the registered regression set with no standard decision changes.",
        "delta" => @cycle.evaluation.dig("comparison", "delta"))
      verify_policy!(@cycle.candidate_policy)
      switched = false
      @cycle.release.with_lock do
        if @cycle.release.policy_version_id == @cycle.baseline_policy_id
          @cycle.release.update!(policy_version: @cycle.candidate_policy, generation: @cycle.release.generation + 1, activated_at: Time.current)
          @switched_generation = @cycle.release.generation
          switched = true
        end
      end
      return finish!("held", [ "The active policy changed during evaluation; this stale candidate was not applied." ]) unless switched

      @cycle.event!("release_switched", "The service release pointer changed atomically.",
        "policy_id" => @cycle.candidate_policy.public_id, "generation" => @switched_generation)
      active = Release.find(@cycle.release_id).policy_version
      raise "Active policy changed before verification" unless active.id == @cycle.candidate_policy_id

      proof = verify_policy!(active)
      @cycle.update!(service_verification: proof.merge("verified" => true, "selection_source" => "active_release",
        "checked_at" => Time.current.iso8601, "wired_paths" => %w[generate diagnose_practice practice review]), activated_at: Time.current)
      @cycle.event!("service_verified", "The actual AI service used the active version and returned the expected decision trace.",
        "policy_id" => active.public_id, "policy_hash" => active.content_hash)
      finish!("adopted", [ "The registered regression gate and active-service verification passed. This is a narrow EXCEPT guard, not a general learning-effect claim." ])
    end

    def verify_policy!(policy)
      witness = @cycle.benchmark.cases.find { _1["operator"] == "except" && _1["solver_answer"] == _1["key"] && _1["baseline_answer"] != _1["key"] }
      raise "No service witness" unless witness

      proof = @client.probe_policy("policy" => policy.context, "case" => witness)
      unless proof["policy_id"] == policy.public_id && proof["policy_hash"] == policy.content_hash && proof["chosen_answer"] == witness["key"] && proof["applied"] == true
        raise "Service policy trace did not verify"
      end
      proof.slice("policy_id", "policy_hash", "chosen_answer", "applied", "reason").merge("expected_answer" => witness["key"])
    end

    def restore_baseline!
      return unless @switched_generation

      @cycle.release.with_lock do
        if @cycle.release.policy_version_id == @cycle.candidate_policy_id && @cycle.release.generation == @switched_generation
          @cycle.release.update!(policy_version: @cycle.baseline_policy, generation: @cycle.release.generation + 1, activated_at: Time.current)
          @cycle.event!("rolled_back", "Application verification failed; the preceding active policy was restored.")
        end
      end
    end

    def finish!(status, reasons)
      @cycle.update!(status: status, decision_reasons: reasons, decided_at: Time.current)
      unless status == "failed"
        @cycle.release.with_lock do
          @cycle.release.update!(source_cursor: [ @cycle.release.source_cursor, @cycle.source_snapshot["source_cursor"].to_i ].max,
            attempt_cursor: [ @cycle.release.attempt_cursor, @cycle.source_snapshot["attempt_cursor"].to_i ].max)
        end
      end
      @cycle.event!(status, reasons.join(" "))
      @cycle.update!(ledger_entry: LedgerExport.entry(@cycle))
    end
  end
end
