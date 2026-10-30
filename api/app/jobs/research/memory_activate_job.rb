module Research
  class MemoryActivateJob < ApplicationJob
    queue_as :research
    class_attribute :ai_client_factory, default: -> { AiService::Client.new(read_timeout: 90) }

    def perform(id)
      cycle = MemoryCycle.find(id)
      return unless cycle.status == "activating" && cycle.evaluation["passed"] == true

      release = MemoryRelease.current
      generation = nil
      release.with_lock do
        unless release.memory_version_id == cycle.baseline_id
          cycle.finish!("held", decision_reasons: [ "The baseline changed while local evaluation was running." ])
          return
        end
        release.update!(memory_version: cycle.candidate, generation: release.generation + 1, activated_at: Time.current)
        generation = release.generation
      end
      proof = ai_client_factory.call.probe_memory("memory" => release.reload.memory_version.context)
      valid = proof["policy_id"] == cycle.candidate.public_id && proof["policy_hash"] == cycle.candidate.content_hash && proof["answer_correct"] == true && proof["runtime_version"] == "gmat-upload-learning-1"
      raise AiService::Error, "Memory application contract failed" unless valid

      release.with_lock do
        raise AiService::Error, "Active version changed before application verification" unless release.memory_version_id == cycle.candidate_id && release.generation == generation
        cycle.finish!("adopted", service_verification: proof.slice("policy_id", "policy_hash", "policy_version", "answer_correct", "runtime_version").merge("verified" => true, "checked_at" => Time.current.iso8601),
          decision_reasons: [ "Reproduced local validation improvement, no validation regression, and the running service used the selected memory version." ])
        release.update!(observation_cursor: [ release.observation_cursor, cycle.registration["source_to_id"].to_i, cycle.observation_ids.max.to_i ].max)
      end
      cycle.event!("adopted", "The selected memory passed a fresh live service contract. Subsequent uploads pin this version.")
    rescue StandardError => e
      if generation
        release.with_lock do
          release.update!(memory_version: cycle.baseline, generation: release.generation + 1, activated_at: Time.current) if release.memory_version_id == cycle.candidate_id && release.generation == generation
        end
      end
      cycle&.finish!("failed", decision_reasons: [ "Service verification failed; prior memory retained or restored (#{e.class.name})." ], service_verification: { "verified" => false })
    end
  end
end
