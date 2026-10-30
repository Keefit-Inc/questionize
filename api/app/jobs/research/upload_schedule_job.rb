module Research
  class UploadScheduleJob < ApplicationJob
    queue_as :research

    def self.request_check
      return unless Rails.cache.write("research/upload-learning/check", true, expires_in: 30.seconds, unless_exist: true)

      set(wait: 30.seconds).perform_later
    end

    def perform
      release = MemoryRelease.current
      return unless release

      release.with_lock do
        expired = MemoryCycle.where(status: %w[generating evaluating]).where("lease_expires_at < ?", Time.current)
        expired.each { _1.finish!("failed", decision_reasons: [ "The local worker lease expired; the running service memory was retained." ]) }
        return if MemoryCycle.where(status: %w[queued generating evaluating activating]).exists?
        return if MemoryCycle.where("leased_at >= ?", Time.current.beginning_of_day).count >= 2
        return if MemoryCycle.where("leased_at > ?", 15.minutes.ago).exists?

        scope = UploadObservation.where("id > ?", release.observation_cursor)
        return unless scope.exists?
        failures = scope.where(outcome: %w[reference_mismatch ai_disagreement])
        return unless scope.distinct.count(:question_fingerprint) >= 3 || failures.exists?
        fresh = (failures.order(:id).limit(10).to_a + scope.order(id: :desc).limit(10).to_a).uniq

        cycle = MemoryCycle.create!(baseline: release.memory_version, observation_ids: fresh.map(&:id),
          trigger: fresh.all?(&:operator_test) ? "operator_research" : "usage_batch",
          registration: { "source_to_id" => scope.maximum(:id), "source_count" => scope.count })
        cycle.event!("queued", "New blind upload observations reached the batch or failure threshold. Originals are not sent to the research server.")
        unless failures.exists?
          cycle.finish!("held", decision_reasons: [ "No reference mismatch or independent-answer disagreement was observed. No paid proposal is needed." ])
          release.update!(observation_cursor: cycle.registration["source_to_id"])
        end
      end
    end
  end
end
