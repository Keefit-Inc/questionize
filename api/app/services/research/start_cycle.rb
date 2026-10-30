module Research
  class StartCycle
    class Unavailable < StandardError; end
    DEFAULT_CRITERIA = { "min_cases" => 35, "min_improvements" => 1, "max_regressions" => 0 }.freeze

    def self.call(requested_by: nil, automatic: false)
      release = Release.bootstrap!
      cycle = nil
      release.with_lock do
        raise Unavailable, "A cycle is already in progress." if release.cycles.in_progress.exists?
        settings = Rails.configuration.x.research_evolution
        raise Unavailable, "The daily proposal limit has been reached." if release.cycles.where(created_at: Time.current.all_day).count >= settings.daily_limit
        benchmark = Benchmark.where(enabled: true, subject: "CR", level: "gmat").order(:id).last
        raise Unavailable, "Import and freeze the replay benchmark first." unless benchmark && benchmark.cases.size >= DEFAULT_CRITERIA["min_cases"]

        evidence = Evidence.new(release).snapshot
        if automatic
          raise Unavailable, "Automatic batches are disabled." unless settings.enabled
          raise Unavailable, "The automatic batch cooldown is active." if release.last_automatic_at && release.last_automatic_at > settings.cooldown_seconds.seconds.ago
          unless evidence["trusted_sources"] >= settings.min_trusted_sources || evidence["new_rated_attempts"] >= settings.min_rated_attempts
            raise Unavailable, "Waiting for enough new trusted observations or rated attempts."
          end
        end
        criteria = DEFAULT_CRITERIA.merge(
          "min_trusted_sources" => settings.min_trusted_sources, "min_rated_attempts" => settings.min_rated_attempts,
          "cooldown_seconds" => settings.cooldown_seconds, "daily_limit" => settings.daily_limit
        )
        cycle = release.cycles.create!(benchmark: benchmark, baseline_policy: release.policy_version, requested_by: requested_by,
          trigger: automatic ? "usage_batch" : "operator_research", source_snapshot: evidence,
          criteria: criteria, code_revision: ENV.fetch("KAMAL_VERSION", ENV.fetch("SOURCE_REVISION", "local-development")))
        cycle.event!("queued", automatic ? "A usage batch met the frozen readiness rules." : "An operator requested a bounded research cycle.",
          "benchmark_hash" => benchmark.content_hash, "n" => benchmark.cases.size)
        release.update!(last_automatic_at: Time.current) if automatic
      end
      CycleJob.perform_later(cycle.id)
      cycle
    end
  end
end
