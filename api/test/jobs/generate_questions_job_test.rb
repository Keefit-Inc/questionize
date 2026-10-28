require "test_helper"

class GenerateQuestionsJobTest < ActiveJob::TestCase
  include ActionCable::TestHelper

  class FakeClient
    attr_reader :payloads

    def initialize(events: [], error: nil)
      @events = events
      @error = error
      @payloads = []
    end

    def generate(payload)
      @payloads << payload
      @events.each { |event| yield event }
      raise @error if @error
    end
  end

  setup do
    @user = User.create!
    @source = Source.for_page!(url: "https://example.com/story", title: "Story", text: ARTICLE_TEXT)
    @run = GenerationRun.create!(user: @user, source: @source, params: { "title" => "Story", "url" => "https://example.com/story", "types" => %w[CR], "difficulty" => "easy", "count_per_type" => 1 })
    @run.cache_text!(ARTICLE_TEXT)
  end

  teardown { GenerateQuestionsJob.ai_client_factory = -> { AiService::Client.new } }

  def run_with(client)
    GenerateQuestionsJob.ai_client_factory = -> { client }
    GenerateQuestionsJob.perform_now(@run.id)
    @run.reload
  end

  test "stores verified items, broadcasts progress without the key, and clears the cached text" do
    client = FakeClient.new(events: [
      { "stage" => "analyze", "message" => "Mapping" },
      { "stage" => "analyzed", "message" => "Main point", "analysis" => { "content_flags" => [] } },
      { "stage" => "question", "index" => 0, "question" => generated_question(correct: "D") },
      { "stage" => "done", "result" => {} }
    ])
    broadcasts = capture_broadcasts(GenerationChannel.broadcasting_for(@run)) { run_with(client) }

    assert_equal "completed", @run.status
    assert_equal ARTICLE_TEXT, client.payloads.first["text"]
    item = @run.items.sole
    assert_equal [ "verified", "public" ], [ item.status, item.visibility ]
    assert_equal 1300.0, item.rating
    assert_equal "D", item.current_version.correct_label
    assert_equal %w[label rationale trap], item.current_version.rationales.first.keys.sort
    assert_equal 10, item.current_version.judge_measurements.count
    assert_equal "pass", item.current_version.verification.dig("judge", "verdict")
    assert_in_delta(-0.7, item.current_version.judge_measurements.find_by(label: "D", measure: "support_delta").value)

    assert_equal %w[analyze analyzed question done], broadcasts.map { _1["stage"] }
    question = broadcasts.find { _1["stage"] == "question" }
    assert_equal item.public_id, question.dig("item", "id")
    assert_not question["item"].key?("correct_label")
    assert_not_includes broadcasts.to_json, "names an alternative cause"

    assert_nil Rails.cache.read(@run.text_cache_key)
    assert_equal %w[analyze analyzed question done], @run.events.map { _1["stage"] }
  end

  test "sensitive articles are held back from the public feed and unverified items stay private" do
    client = FakeClient.new(events: [
      { "stage" => "analyzed", "message" => "m", "analysis" => { "content_flags" => [ "graphic_violence" ] } },
      { "stage" => "question", "index" => 0, "question" => generated_question },
      { "stage" => "question", "index" => 1, "question" => generated_question(verified: false) },
      { "stage" => "done", "result" => {} }
    ])
    run_with(client)
    held, unverified = @run.items.order(:id).to_a
    assert_equal [ "held", [ "graphic_violence" ], nil ], [ held.visibility, held.content_flags, held.published_at ]
    assert_equal [ "unverified", "private" ], [ unverified.status, unverified.visibility ]
  end

  test "a declined page ends the run with the reason" do
    client = FakeClient.new(events: [ { "stage" => "declined", "reason" => "not_an_article", "message" => "This is a shop." } ])
    broadcasts = capture_broadcasts(GenerationChannel.broadcasting_for(@run)) { run_with(client) }
    assert_equal "declined", @run.status
    assert_equal({ "stage" => "declined", "reason" => "not_an_article", "message" => "This is a shop." }, broadcasts.last)
    assert_empty @run.items
  end

  test "an AI service failure marks the run failed without leaking details" do
    client = FakeClient.new(events: [ { "stage" => "analyze", "message" => "Mapping" } ], error: AiService::Error.new("500 secret-internal-detail"))
    broadcasts = capture_broadcasts(GenerationChannel.broadcasting_for(@run)) { run_with(client) }
    assert_equal "failed", @run.status
    assert_equal "failed", broadcasts.last["stage"]
    assert_not_includes broadcasts.last["message"], "secret-internal-detail"
    assert_nil Rails.cache.read(@run.text_cache_key)
  end

  test "a stream that stops without a final event fails the run" do
    run_with(FakeClient.new(events: [ { "stage" => "analyze", "message" => "Mapping" } ]))
    assert_equal "failed", @run.status
  end

  test "expired text fails fast without calling the AI service" do
    Rails.cache.delete(@run.text_cache_key)
    client = FakeClient.new
    run_with(client)
    assert_equal "failed", @run.status
    assert_empty client.payloads
  end
end
