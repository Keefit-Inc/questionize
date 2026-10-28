module GenerationRuns
  # Turns AI service stream events into stored items and client-safe broadcast payloads.
  class Recorder
    MAX_STORED_EVENTS = 300

    def initialize(run)
      @run = run
      @content_flags = []
    end

    # Returns the payload to broadcast for this event.
    def record(event)
      payload =
        case event["stage"]
        when "analyzed" then analyzed(event)
        when "question" then question(event)
        when "map" then argument_map(event)
        when "done" then finish("completed", { "stage" => "done", "count" => @run.items.count })
        when "declined" then finish("declined", event.slice("stage", "reason", "message"))
        when "failed" then finish("failed", event.slice("stage", "message"))
        else event
        end
      remember(payload)
      payload
    end

    def fail!(message)
      record("stage" => "failed", "message" => message)
    end

    private

    def analyzed(event)
      @content_flags = Array(event.dig("analysis", "content_flags"))
      { "stage" => "analyzed", "message" => event["message"], "content_flags" => @content_flags }
    end

    def question(event)
      item = persist(event.fetch("question"))
      { "stage" => "question", "index" => event["index"], "item" => ItemPayload.new(item, revealed: false).as_json }
    end

    def argument_map(event)
      @run.update!(result: event.fetch("map"))
      { "stage" => "map", "map" => MapPayload.new(@run, user: @run.user).as_json }
    end

    def persist(generated)
      q = generated.fetch("question")
      verification = generated.fetch("verification")
      verified = verification["verified"] == true

      Item.transaction do
        item = Item.create!(
          source: @run.source, generation_run: @run, family: q.fetch("type"), subtype: q.fetch("subtype"),
          status: verified ? "verified" : "unverified", visibility: visibility(verified),
          content_flags: @content_flags, rating: Item.start_rating(@run.params["difficulty"]),
          published_at: verified && @content_flags.empty? ? Time.current : nil
        )
        version = item.versions.create!(
          version: 1, passage: q.fetch("passage"), stem: q.fetch("stem"), choices: q.fetch("choices"),
          correct_label: q.fetch("correct_label"), explanation: q.fetch("explanation"),
          rationales: q.fetch("choice_rationales").map { |r| r.slice("label", "rationale", "trap") },
          skill: q["skill"], source_anchor: q["source_anchor"],
          verification: verification.merge("judge" => judge_summary(generated["judge"])).compact
        )
        store_judge_measurements(version, generated["judge"])
        item.update!(current_version: version)
        item
      end
    end

    def judge_summary(judge)
      judge&.slice("judge_version", "verdict", "measure", "direction", "margin", "key_first_rate", "runner_up", "judges", "samples")
    end

    def store_judge_measurements(version, judge)
      return unless judge

      rows = Array(judge["options"]).flat_map do |option|
        %w[support_delta necessity].filter_map do |measure|
          m = option[measure] or next
          { item_version_id: version.id, label: option["label"], measure: measure, value: m["value"],
            ci_low: m["ci_low"], ci_high: m["ci_high"], judge_version: judge["judge_version"] }
        end
      end
      JudgeMeasurement.insert_all!(rows) if rows.any?
    end

    # Unverified items stay with their creator; sensitive ones wait for review before the public feed.
    def visibility(verified)
      return "private" unless verified

      @content_flags.empty? ? "public" : "held"
    end

    def finish(status, payload)
      @run.update!(status: status)
      payload
    end

    def remember(payload)
      # Stored events are a progress log; items and maps are read from their own records.
      compact = payload.except("item", "map").merge(payload["item"] ? { "item_id" => payload.dig("item", :id) } : {})
      @run.events = (@run.events + [ compact ]).last(MAX_STORED_EVENTS)
      @run.save!
    end
  end
end
