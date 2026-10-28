require "test_helper"

class Api::V1::ItemsControllerTest < ActionDispatch::IntegrationTest
  include ActionCable::TestHelper
  setup do
    @user = User.create!
    @item = create_item(correct_label: "C")
  end

  test "hides the key, explanations and tallies before an attempt" do
    get api_v1_item_path(@item.public_id), headers: auth_headers(@user)
    assert_response :ok
    body = response.parsed_body
    assert_equal false, body["revealed"]
    %w[correct_label explanation rationales tally source_anchor judge].each { |field| assert_not body.key?(field), field }
  end

  test "an attempt reveals everything and reports the rating change" do
    post api_v1_item_attempts_path(@item.public_id), params: { label: "c", time_ms: 30_000 }, headers: auth_headers(@user), as: :json
    assert_response :created
    body = response.parsed_body
    assert body["correct"]
    assert body["rated"]
    assert_equal "C", body.dig("item", "correct_label")
    assert_equal 1, body.dig("item", "tally", "C")
    assert_in_delta 1520.0, body.dig("rating_changes", "CR:assumption", "after"), 1e-9

    get api_v1_item_path(@item.public_id), headers: auth_headers(@user)
    assert response.parsed_body["revealed"]
  end

  test "judge measurements arrive with the reveal" do
    run = GenerationRun.create!(user: @user, params: { "difficulty" => "medium" })
    GenerationRuns::Recorder.new(run).record("stage" => "question", "index" => 0, "question" => generated_question(correct: "B"))
    item = run.items.sole

    post api_v1_item_attempts_path(item.public_id), params: { label: "B" }, headers: auth_headers(@user), as: :json
    judge = response.parsed_body.dig("item", "judge")
    assert_equal [ "pass", "support_delta" ], judge.values_at("verdict", "measure")
    option_b = judge["options"].find { _1["label"] == "B" }
    assert_in_delta(-0.7, option_b.dig("support_delta", "value"))
    assert_not response.parsed_body.dig("item", "verification").key?("judge")
  end

  test "the feed lists public items newest first and reveals only what the user answered" do
    older = create_item(family: "RC", subtype: "inference")
    older.update!(published_at: 2.days.ago)
    create_item(visibility: "private")
    Learning::RecordAttempt.call(user: @user, item: @item, chosen_label: "C")

    get api_v1_items_path, headers: auth_headers(@user)
    ids = response.parsed_body["items"].map { _1["id"] }
    assert_equal [ @item.public_id, older.public_id ], ids
    assert_equal [ true, false ], response.parsed_body["items"].map { _1["revealed"] }

    get api_v1_items_path(family: "RC"), headers: auth_headers(@user)
    assert_equal [ older.public_id ], response.parsed_body["items"].map { _1["id"] }
  end

  test "private items are only visible to the user who generated them" do
    owner = User.create!
    run = GenerationRun.create!(user: owner)
    private_item = create_item(visibility: "private")
    private_item.update!(generation_run: run)

    get api_v1_item_path(private_item.public_id), headers: auth_headers(@user)
    assert_response :not_found
    get api_v1_item_path(private_item.public_id), headers: auth_headers(owner)
    assert_response :ok
  end

  test "an attempt broadcasts the new tally to the item's channel" do
    assert_broadcasts(ItemChannel.broadcasting_for(@item), 1) do
      post api_v1_item_attempts_path(@item.public_id), params: { label: "A" }, headers: auth_headers(@user), as: :json
    end
  end

  test "me returns XP and ratings by skill" do
    Learning::RecordAttempt.call(user: @user, item: @item, chosen_label: "C")
    get api_v1_me_path, headers: auth_headers(@user)
    body = response.parsed_body
    assert_equal 10, body["xp"]
    assert_equal %w[CR CR:assumption overall], body["ratings"].map { _1["skill"] }
    assert body["ratings"].all? { _1["provisional"] }
  end

  test "flags need an answer first and can start a review" do
    post api_v1_item_feedback_path(@item.public_id), params: { kind: "flag", reason: "typo" }, headers: auth_headers(@user), as: :json
    assert_response :forbidden

    2.times do
      other = User.create!
      Learning::RecordAttempt.call(user: other, item: @item, chosen_label: "A")
      Feedback.create!(user: other, item_version: @item.current_version, kind: "flag", reason: "two_answers")
    end
    Learning::RecordAttempt.call(user: @user, item: @item, chosen_label: "A")
    post api_v1_item_feedback_path(@item.public_id), params: { kind: "flag", reason: "two_answers", comment: "D works too" }, headers: auth_headers(@user), as: :json
    assert_response :created
    assert response.parsed_body["review_started"]
    assert_equal "under_review", @item.reload.status

    post api_v1_item_feedback_path(@item.public_id), params: { kind: "flag", reason: "nonsense" }, headers: auth_headers(@user), as: :json
    assert_response :unprocessable_entity
  end

  test "rejects labels outside A-E" do
    post api_v1_item_attempts_path(@item.public_id), params: { label: "Z" }, headers: auth_headers(@user), as: :json
    assert_response :unprocessable_entity
  end

  test "unknown items are 404" do
    get api_v1_item_path("missing"), headers: auth_headers(@user)
    assert_response :not_found
  end
end
