module GenerationRuns
  # Turns AI service stream events into stored items and client-safe broadcast payloads.
  class Recorder
    MAX_STORED_EVENTS = 300

    def initialize(run)
      @run = run
      @content_flags = []
    end

    QUESTION_TTL = 1.hour

    def self.question_cache_key(entry)
      "error_log_entries/#{entry.id}/question"
    end

    # Returns the payload to broadcast for this event.
    def record(event)
      payload =
        case event["stage"]
        when "analyzed" then analyzed(event)
        when "question" then question(event)
        when "map" then argument_map(event)
        when "diagnosis" then error_log_entry(event)
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

    def persist(generated, origin: "generated")
      q = generated.fetch("question")
      verified = generated.dig("verification", "verified") == true

      Item.transaction do
        item = Item.create!(
          source: @run.source, generation_run: @run, family: q.fetch("type"), subtype: q.fetch("subtype"),
          status: verified ? "verified" : "unverified", visibility: visibility(verified), origin: origin,
          content_flags: @content_flags, rating: Item.start_rating(@run.params["difficulty"]),
          level: Level.valid?(@run.params["level"]) ? @run.params["level"] : Level.for(@run.user), scene: q["scene"].presence,
          published_at: verified && @content_flags.empty? ? Time.current : nil
        )
        version = ItemVersion.create_from_generated!(item: item, generated: generated, version: 1)
        item.update!(current_version: version)
        item
      end
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

    # The diagnosis becomes a private error-log entry. Practice items are new questions written
    # from the question's abstract design, so once verified they join the shared bank like any
    # other item; the abstract design (if it passed the leak checks) becomes an observation.
    def error_log_entry(event)
      entry = nil
      Item.transaction do
        observation = observation_from(event)
        entry = Learning::ErrorLogEntry.create!(
          user: @run.user, generation_run: @run, source_observation: observation,
          book: @run.params["book"], page: @run.params["page"], number: @run.params["number"],
          chosen_label: @run.params["chosen_label"], diagnosis: event.fetch("diagnosis"), dataset: @run.params["dataset"]
        )
        Array(event["practice"]).each { |generated| persist(generated, origin: "pattern") }
      end
      # The same design, re-pitched for other levels in the background (docs/LEARNING_MODEL.md §4).
      LevelPracticeJob.fan_out(entry.source_observation, learner_level: Level.for(@run.user)) if entry.source_observation
      # The printed question waits in the cache for the learner's device to fetch it once; it is
      # never stored with the entry, the run's events or the broadcast.
      question = event["source_question"]
      Rails.cache.write(self.class.question_cache_key(entry), question, expires_in: QUESTION_TTL) if question.present?
      { "stage" => "diagnosis", "entry" => ErrorLogPayload.new(entry, user: @run.user).as_json, "question_ready" => question.present? }
    end

    def observation_from(event)
      return unless event["observation"]

      Knowledge::SourceObservation.create!(
        source_kind: "print_scan", source_ref: source_ref, stated_level: event.dig("observation", "stated_level"),
        observed: event["observation"].merge(
          "misconception" => event.dig("diagnosis", "misconception"), "chosen_trap" => event.dig("diagnosis", "chosen_trap"),
          # Whether the key behind this design was checked against the book (the learning signal, R2).
          "key_verdict" => event.dig("diagnosis", "key_check", "verdict"), "dataset" => @run.params["dataset"],
          "label_source" => @run.params["answer_key"].present? ? "user_provided_key" : "model_inferred",
          "label_status" => @run.params["answer_key"].present? ? event.dig("diagnosis", "key_check", "verdict") : "unconfirmed"
        ).merge("level" => @run.params["level"] || Level.for(@run.user)).compact,
        extractor: "diagnose", leak_checks: event["leak_checks"] || {},
        knowledge_origin: "user_experience", evidence_status: "ai_estimated",
        rights_scope: event.dig("leak_checks", "passed") == true ? "shared_abstract" : "private_research",
        provenance: { "derivation" => "model_extracted", "label_origin" => @run.params["answer_key"].present? ? "user_provided_key" : "model_inferred",
          "verification" => "model_key_check", "namespace" => "user_experience" }
      )
    end

    # A keyed hash of where the question lives: counts independent sources and honors removal
    # requests without revealing the book (docs/KNOWLEDGE_MODEL.md §3.9).
    def source_ref
      location = @run.params.values_at("book", "page", "number").map { _1.to_s.downcase.squish }.join("|")
      location = "unlabeled|#{@run.id}" if location.delete("|").empty?
      OpenSSL::HMAC.hexdigest("SHA256", Rails.application.secret_key_base, location)
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
