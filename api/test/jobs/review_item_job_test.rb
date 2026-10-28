require "test_helper"

class ReviewItemJobTest < ActiveJob::TestCase
  class FakeClient
    def initialize(result = nil, error: nil, **result_hash) = (@result, @error = result || result_hash, error)
    attr_reader :payload

    def review(payload)
      @payload = payload
      raise @error if @error

      @result
    end
  end

  setup do
    @item = create_item(correct_label: "B")
    @item.update!(rating: 1580, attempts_count: 12, correct_count: 7)
    Learning::ChoiceTally.increment!(@item.current_version, "B")
    @review = @item.reviews.create!(from_version: @item.current_version, trigger: "repeated_flags")
    @item.update!(status: "under_review")
  end

  teardown { ReviewItemJob.ai_client_factory = -> { AiService::Client.new } }

  def run_with(client)
    ReviewItemJob.ai_client_factory = -> { client }
    ReviewItemJob.perform_now(@review.id)
    [ @item.reload, @review.reload ]
  end

  def decision(verdict) = { "verdict" => verdict, "findings" => [ "D is also defensible" ], "revision_guidance" => "" }

  test "keep restores the item and records the findings" do
    client = FakeClient.new("decision" => decision("keep"))
    item, review = run_with(client)
    assert_equal [ "verified", "done", "keep" ], [ item.status, review.status, review.verdict ]
    assert_equal "B", client.payload[:question][:correct_label]
  end

  test "retire takes the item out of the feed" do
    item, = run_with(FakeClient.new("decision" => decision("retire")))
    assert_equal "retired", item.status
    assert_not Item.listed.exists?(item.id)
  end

  test "a verified revision with the same key becomes version 2 and keeps tallies and rating" do
    revised = generated_question(correct: "B").deep_merge("question" => { "stem" => "Which most weakens the claim? (revised)" })
    item, review = run_with(FakeClient.new("decision" => decision("revise"), "revised" => revised))

    assert_equal 2, item.current_version.version
    assert_equal review.from_version, item.current_version.parent_version
    assert_equal item.current_version, review.to_version
    assert_equal "verified", item.status
    assert_equal 1580.0, item.rating
    assert_equal 1, item.current_version.tally["B"]
    assert_equal 10, item.current_version.judge_measurements.count
  end

  test "a revision that changes the key resets the item's statistics" do
    revised = generated_question(correct: "D")
    item, = run_with(FakeClient.new("decision" => decision("revise"), "revised" => revised))
    assert_equal [ "D", 1500.0, 0 ], [ item.current_version.correct_label, item.rating, item.attempts_count ]
    assert_equal 0, item.current_version.tally.values.sum
  end

  test "an unverified revision or an AI failure leaves the item flagged for a person" do
    item, = run_with(FakeClient.new("decision" => decision("revise"), "revised" => generated_question(verified: false)))
    assert_equal [ "flagged", 1 ], [ item.status, item.current_version.version ]

    @item.update!(status: "under_review")
    item, review = run_with(FakeClient.new(error: AiService::Error.new("down")))
    assert_equal [ "flagged", "failed" ], [ item.status, review.status ]
  end
end
