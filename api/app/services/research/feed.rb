module Research
  class Feed
    def self.public_data(user: nil)
      release = Release.find_by(subject: "CR", level: "gmat", capability: "C3.1")
      settings = Rails.configuration.x.research_evolution
      snapshot = release ? Evidence.new(release).snapshot : { "trusted_sources" => 0, "new_rated_attempts" => 0, "unconfirmed_sources" => 0 }
      readiness = if !release || !Benchmark.where(enabled: true).where("jsonb_array_length(cases) >= 35").exists?
        "benchmark_or_baseline_required"
      elsif release.cycles.in_progress.exists?
        "cycle_in_progress"
      elsif !settings.enabled
        "automatic_batches_disabled"
      elsif release.cycles.where(created_at: Time.current.all_day).count >= settings.daily_limit
        "daily_proposal_limit_reached"
      elsif release.last_automatic_at && release.last_automatic_at > settings.cooldown_seconds.seconds.ago
        "cooldown_active"
      elsif snapshot["trusted_sources"] >= settings.min_trusted_sources || snapshot["new_rated_attempts"] >= settings.min_rated_attempts
        "ready_for_next_usage_trigger"
      else
        "waiting_for_trusted_evidence"
      end
      {
        schema_version: 1, scope: { subject: "CR", level: "gmat", capability: "C3.1", policy_kind: "judge_operator" },
        active_policy: release&.public_data,
        automation: { enabled: settings.enabled, min_trusted_sources: settings.min_trusted_sources,
          min_rated_attempts: settings.min_rated_attempts, cooldown_seconds: settings.cooldown_seconds,
          daily_limit: settings.daily_limit, daily_used: release&.cycles&.where(created_at: Time.current.all_day)&.count || 0,
          eligible_sources: snapshot["trusted_sources"], unconfirmed_sources: snapshot["unconfirmed_sources"],
          new_rated_attempts: snapshot["new_rated_attempts"], readiness: readiness },
        knowledge_evidence: {
          origins: Knowledge::SourceObservation.group(:knowledge_origin).count,
          statuses: Knowledge::SourceObservation.group(:evidence_status).count,
          separation: "Expert references and user experience have separate namespaces. AI extraction is not expert authorship; model consensus is not a confirmed label."
        },
        verification_service: verification_service,
        cycles: Cycle.includes(:baseline_policy, :candidate_policy, :benchmark, :events).order(id: :desc).limit(30).map(&:public_data),
        operator: { authenticated: user.present?, curator: user&.curator == true }.merge(user ? { handle: user.handle } : {})
      }
    end

    def self.verification_service
      return { status: "not_probed" } unless Rails.env.production?

      Rails.cache.fetch("research/verification-health", expires_in: 30.seconds) do
        AiService::Client.new.health.merge("status" => "observed", "observed_at" => Time.current.iso8601)
      end
    rescue AiService::Error
      { status: "unavailable" }
    end

    def self.merge_scoreboard(data)
      cycles = Cycle.where(status: Cycle::TERMINAL).order(:id).to_a
      live_runs = cycles.map { LedgerExport.run_data(_1) }
      memory_cycles = MemoryCycle.where(status: MemoryCycle::TERMINAL).includes(:candidate).select { MemoryLedgerExport.entry(_1) }
      live_runs += memory_cycles.map { MemoryLedgerExport.run_data(_1) }
      ids = live_runs.map { _1["run_id"] }
      runs = Array(data["runs"]).reject { ids.include?(_1["run_id"]) } + live_runs
      records = Array(data["records"]).reject { ids.include?(_1["run_id"]) } + cycles.flat_map { LedgerExport.records(_1) } + memory_cycles.flat_map { MemoryLedgerExport.records(_1) }
      data.merge("runs" => runs, "records" => records, "subjects" => (Array(data["subjects"]) + (cycles.any? ? [ "CR" ] : [])).uniq.sort,
        "updated_at" => runs.map { _1["started_at"] }.compact.max)
    end
  end
end
