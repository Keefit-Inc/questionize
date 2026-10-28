# Streams a generation run from the AI service, stores items as they arrive and
# rebroadcasts progress on GenerationChannel (docs/ARCHITECTURE.md §5.1).
class GenerateQuestionsJob < ApplicationJob
  queue_as :default

  # Swappable in tests; production talks to the AI service over HTTP.
  class_attribute :ai_client_factory, default: -> { AiService::Client.new }

  def perform(run_id)
    run = GenerationRun.find(run_id)
    recorder = GenerationRuns::Recorder.new(run)
    text = Rails.cache.read(run.text_cache_key)
    return broadcast(run, recorder.fail!("The article text expired before generation started. Please try again.")) unless text

    run.update!(status: "running")
    ai_client_factory.call.generate(request_payload(run, text)) { |event| broadcast(run, recorder.record(event)) }
    broadcast(run, recorder.fail!("The AI service ended the stream unexpectedly.")) if run.reload.status == "running"
  rescue AiService::Error => e
    Rails.logger.error("[GenerateQuestionsJob] run #{run_id}: #{e.message}")
    broadcast(run, recorder.fail!("Question generation is unavailable right now. Please try again shortly."))
  ensure
    Rails.cache.delete(run.text_cache_key) if run
  end

  private

  def request_payload(run, text)
    run.params.slice("title", "url", "selection", "types", "difficulty", "count_per_type").merge("text" => text)
  end

  def broadcast(run, payload)
    GenerationChannel.broadcast_to(run, payload)
  end
end
