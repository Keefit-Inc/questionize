require "test_helper"

class Api::V1::ReviewControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = User.create!
    @item = create_item(correct_label: "B")
  end

  def answer(label, user: @user)
    post api_v1_item_attempts_path(@item.public_id), params: { label: label }, headers: auth_headers(user), as: :json
  end

  def cards(archived: false)
    get api_v1_review_path, params: { archived: archived }, headers: auth_headers(@user)
    response.parsed_body["cards"]
  end

  test "a first miss puts a bank item on the review list; a first correct answer doesn't" do
    answer("A")
    assert_equal [ [ "item", "missed", @item.public_id ] ], cards.map { [ _1["kind"], _1["reason"], _1.dig("item", "id") ] }
    other = User.create!
    answer("B", user: other)
    assert_empty other.saved_items
  end

  test "snapped questions and saved items share one list, and archiving moves them out of it" do
    run = GenerationRun.create!(user: @user, kind: "error_log", params: {})
    GenerationRuns::Recorder.new(run).record(diagnosis_event)
    entry = @user.error_log_entries.sole
    put api_v1_item_save_path(@item.public_id), headers: auth_headers(@user), as: :json
    assert_equal %w[item snap], cards.map { _1["kind"] }

    patch api_v1_error_log_path(entry), params: { archived: true }, headers: auth_headers(@user), as: :json
    put api_v1_item_save_path(@item.public_id), params: { archived: true }, headers: auth_headers(@user), as: :json
    assert_empty cards
    assert_equal %w[item snap], cards(archived: true).map { _1["kind"] }

    patch api_v1_error_log_path(entry), params: { archived: false }, headers: auth_headers(@user), as: :json
    assert_equal [ "snap" ], cards.map { _1["kind"] }
    delete api_v1_item_save_path(@item.public_id), headers: auth_headers(@user)
    assert_empty cards(archived: true)
  end

  test "one vote per learner, shown with the revealed item" do
    answer("B")
    post api_v1_item_feedback_path(@item.public_id), params: { kind: "up" }, headers: auth_headers(@user), as: :json
    post api_v1_item_feedback_path(@item.public_id), params: { kind: "down" }, headers: auth_headers(@user), as: :json
    assert_equal({ "up" => 0, "down" => 1, "mine" => "down" }, response.parsed_body["votes"])
    get api_v1_item_path(@item.public_id), headers: auth_headers(@user)
    assert_equal "down", response.parsed_body.dig("votes", "mine")
  end
end
