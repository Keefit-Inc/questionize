require "test_helper"

class Api::V1::LevelsTest < ActionDispatch::IntegrationTest
  setup { @user = User.create! }

  test "a learner picks a level; invalid levels are refused" do
    patch api_v1_me_path, params: { level: "middle" }, headers: auth_headers(@user), as: :json
    assert_equal "middle", @user.reload.level
    get api_v1_me_path, headers: auth_headers(@user)
    assert_equal "middle", response.parsed_body["level"]
    patch api_v1_me_path, params: { level: "kindergarten" }, headers: auth_headers(@user), as: :json
    assert_response :unprocessable_entity
  end

  test "new generations and snapped questions are written for the learner's level" do
    @user.update!(level: "elementary")
    post api_v1_generations_path, params: { url: "https://example.com/a", title: "A", text: "x" * 300 }, headers: auth_headers(@user), as: :json
    assert_equal "elementary", GenerationRun.last.params["level"]
    run = GenerationRun.create!(user: @user, kind: "questions", params: { "level" => "elementary" })
    item = GenerationRuns::Recorder.new(run).send(:persist, generated_question)
    assert_equal "elementary", item.level
  end

  test "the bank can be filtered by level" do
    create_item.update!(level: "lsat")
    create_item.update!(level: "middle")
    get api_v1_items_path, params: { level: "middle" }, headers: auth_headers(@user)
    assert_equal [ "middle" ], response.parsed_body["items"].map { _1["level"] }
  end

  test "recommendations target the weakest skill at the learner's level, pitched below the learner's rating" do
    @user.update!(level: "lsat")
    @user.rating_for("CR:flaw").update!(rating: 1300, attempts: 4)
    @user.rating_for("CR:weaken").update!(rating: 1700, attempts: 4)
    near = create_item(subtype: "flaw").tap { _1.update!(level: "lsat", rating: 1160) }
    far = create_item(subtype: "flaw").tap { _1.update!(level: "lsat", rating: 1700) }
    create_item(subtype: "flaw").update!(level: "gmat", rating: 1150)
    done = create_item(subtype: "flaw").tap { _1.update!(level: "lsat", rating: 1150) }
    Learning::Attempt.create!(user: @user, item: done, item_version: done.current_version, chosen_label: "A", correct: false, skill: done.skill, rated: false)

    get api_v1_recommendations_path, headers: auth_headers(@user)
    ids = response.parsed_body["items"].map { _1.dig("item", "id") }
    assert_equal near.public_id, ids.first
    assert_includes ids, far.public_id
    assert_not_includes ids, done.public_id
    assert_match(/Flaw is one of your weaker skills/, response.parsed_body.dig("items", 0, "reason"))
    assert_equal false, response.parsed_body.dig("items", 0, "item", "revealed")
  end
end
