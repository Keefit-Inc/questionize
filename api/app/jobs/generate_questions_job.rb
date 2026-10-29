# Streams a run from the AI service (questions, or an argument map), stores what it produces
# and rebroadcasts progress on GenerationChannel (docs/ARCHITECTURE.md §5.0, §5.1).
class GenerateQuestionsJob < ApplicationJob
  queue_as :default

  # Swappable in tests; production talks to the AI service over HTTP.
  class_attribute :ai_client_factory, default: -> { AiService::Client.new }

  def perform(run_id)
    run = GenerationRun.find(run_id)
    recorder = GenerationRuns::Recorder.new(run)
    text = Rails.cache.read(run.text_cache_key)
    Rails.cache.delete(run.text_cache_key) if run.kind == "error_log" # the photo is read once, then gone
    return broadcast(run, recorder.fail!("The input expired before processing started. Please try again.")) unless text

    run.update!(status: "running")
    client = ai_client_factory.call
    payload = request_payload(run, text)
    handle = ->(event) { broadcast(run, recorder.record(event)) }
    case run.kind
    when "map" then client.map(payload.slice("title", "url", "selection", "text"), &handle)
    when "error_log" then client.diagnose(diagnose_payload(run, text), &handle)
    else client.generate(payload, &handle)
    end
    broadcast(run, recorder.fail!("The AI service ended the stream unexpectedly.")) if run.reload.status == "running"
  rescue AiService::Error => e
    Rails.logger.error("[GenerateQuestionsJob] run #{run_id}: #{e.message}")
    broadcast(run, recorder.fail!("Question generation is unavailable right now. Please try again shortly."))
  ensure
    Rails.cache.delete(run.text_cache_key) if run
  end

  private

  def request_payload(run, text)
    run.params.slice("title", "url", "selection", "types", "difficulty", "count_per_type").merge("text" => text, "level" => run.params["level"] || Level.for(run.user))
  end

  def broadcast(run, payload)
    GenerationChannel.broadcast_to(run, payload)
  end

  def diagnose_payload(run, text)
    { "images" => photo_parts(text), "chosen_label" => run.params["chosen_label"], "answer_key" => run.params["answer_key"],
      "level" => Level.for(run.user), "practice_count" => run.params["learn_only"] ? 0 : 2 }.compact
  end

  # The cached photo parts: a JSON list of data URLs (a single data URL from older clients).
  def photo_parts(text)
    text.to_s.start_with?("[") ? JSON.parse(text) : [ text ]
  end
end
