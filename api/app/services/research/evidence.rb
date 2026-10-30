module Research
  class Evidence
    def initialize(release)
      @release = release
    end

    def sources
      Knowledge::SourceObservation.where("id > ?", @release.source_cursor).where("observed->>'family' = 'CR'")
        .where("observed->>'level' = 'gmat'").where("observed->>'key_verdict' IN ('agrees', 'upheld', 'book')")
        .where("leak_checks->>'passed' = 'true'")
    end

    def attempts
      Learning::Attempt.joins(:item).where(rated: true).where("attempts.id > ?", @release.attempt_cursor)
        .where(items: { family: "CR", level: "gmat" })
    end

    def snapshot
      source_ids = sources.order(:id).limit(100).pluck(:id)
      attempt_ids = attempts.order(:id).limit(100).pluck("attempts.id")
      {
        "trusted_sources" => sources.distinct.count(:source_ref), "new_rated_attempts" => attempts.count,
        "source_observation_ids" => source_ids, "rated_attempt_ids" => attempt_ids,
        "source_from" => @release.source_cursor, "attempt_from" => @release.attempt_cursor,
        "source_cursor" => sources.maximum(:id) || @release.source_cursor, "attempt_cursor" => attempts.maximum("attempts.id") || @release.attempt_cursor
      }
    end

    def self.request_check
      return unless Rails.configuration.x.research_evolution.enabled
      return unless Rails.cache.write("research/evolution/check", true, expires_in: 1.minute, unless_exist: true)

      ScheduleJob.set(wait: 1.minute).perform_later
    rescue StandardError => e
      # Research scheduling must not turn a successfully saved learner response into an API
      # failure. The recurring readiness check catches up from the durable source records.
      Rails.logger.warn("[Research::Evidence] readiness scheduling unavailable: #{e.class.name}")
      nil
    end
  end
end
