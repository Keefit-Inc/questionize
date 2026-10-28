require "test_helper"

class Api::V1::ItemsControllerTest < ActionDispatch::IntegrationTest
  setup do
    @user = User.create!
    @item = create_item(correct_label: "C")
  end

  test "hides the key, explanations and tallies before an attempt" do
    get api_v1_item_path(@item.public_id), headers: auth_headers(@user)
    assert_response :ok
    body = response.parsed_body
    assert_equal false, body["revealed"]
    %w[correct_label explanation rationales tally source_anchor].each { |field| assert_not body.key?(field), field }
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

  test "rejects labels outside A-E" do
    post api_v1_item_attempts_path(@item.public_id), params: { label: "Z" }, headers: auth_headers(@user), as: :json
    assert_response :unprocessable_entity
  end

  test "unknown items are 404" do
    get api_v1_item_path("missing"), headers: auth_headers(@user)
    assert_response :not_found
  end
end
