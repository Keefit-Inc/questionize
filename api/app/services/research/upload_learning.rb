module Research
  class UploadLearning
    MEASURES = %w[main_matches_reference control_matches_reference models_agree main_model control_model logical_calls runtime_version memory_hash].freeze

    def self.record(run, payload)
      return unless run.params["level"] == "gmat"
      return UploadObservation.find_by(generation_run: run) if UploadObservation.exists?(generation_run: run)

      version = MemoryVersion.find_by(public_id: run.params["learning_policy_id"])
      if version && payload.dig("measurements", "memory_hash") != version.content_hash
        raise ArgumentError, "The recorded solver version does not match the request-pinned memory"
      end
      status = payload.fetch("reference_status")
      status = "supplied_reference" if status == "confirmed_reference" && !run.params["source_attested"]
      observation = UploadObservation.create!(generation_run: run, memory_version: version,
        question_fingerprint: payload.fetch("question_fingerprint"), reference_status: status,
        reference_source: payload.fetch("reference_source"), knowledge_origin: payload.fetch("knowledge_origin"),
        subtype: payload.fetch("subtype"), outcome: payload.fetch("outcome"),
        abstract_evidence: payload.fetch("abstract_evidence").slice("failure_kind", "lesson", "competency", "key_rule"),
        measurements: payload.fetch("measurements").slice(*MEASURES), operator_test: run.params["operator_test"] == true)
      rollback_regression(observation)
      observation
    end

    def self.rollback_regression(observation)
      return unless observation.reference_status == "confirmed_reference" && observation.measurements["main_matches_reference"] == false && observation.measurements["control_matches_reference"] == true

      release = MemoryRelease.current
      release&.with_lock do
        version = observation.memory_version
        if version&.parent && release.memory_version_id == version.id
          release.update!(memory_version: version.parent, generation: release.generation + 1, activated_at: Time.current)
          cycle = MemoryCycle.find_by(candidate: version, status: "adopted")
          cycle&.finish!("rolled_back", decision_reasons: [ "A new confirmed reference exposed a candidate regression against its control; the parent version was restored." ])
          cycle&.event!("rolled_back", "Confirmed-source online regression; prior memory restored.")
        end
      end
    end

    def self.feed
      release = MemoryRelease.current
      worker = WorkerCredential.where(revoked_at: nil).maximum(:last_seen_at)
      fresh = release ? UploadObservation.where("id > ?", release.observation_cursor) : UploadObservation.none
      daily_used = MemoryCycle.where("leased_at >= ?", Time.current.beginning_of_day).count
      {
        schema_version: 1, runtime: "gmat-upload-learning-1", protocol: "E11", protocol_version: 1,
        storage: "Original questions, reference keys and expert explanations remain on user devices and the operator's local research files. Server research records contain abstract evidence only.",
        active_memory: release&.public_data,
        worker: { online: worker.present? && worker > 2.minutes.ago, last_seen_at: worker, mode: "private_local_evaluation" },
        totals: { uploads: UploadObservation.where(operator_test: false).count,
          operator_checks: UploadObservation.where(operator_test: true).count,
          reference_statuses: UploadObservation.where(operator_test: false).group(:reference_status).count,
          outcomes: UploadObservation.where(operator_test: false).group(:outcome).count },
        observations: UploadObservation.includes(:memory_version).order(id: :desc).limit(40).map(&:public_data),
        cycles: MemoryCycle.includes(:baseline, :candidate).order(id: :desc).limit(20).map(&:public_data),
        budget: { daily_cycles: 2, daily_used: daily_used, waiting_observations: fresh.count,
          observation_batch: 3, early_failure_trigger: 1, cooldown_minutes: 15 }
      }
    end
  end
end
