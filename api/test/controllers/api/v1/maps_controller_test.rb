require "test_helper"

class Api::V1::MapsControllerTest < ActionDispatch::IntegrationTest
  include ActiveJob::TestHelper

  setup do
    @user = User.create!
    @params = { url: "https://example.com/op-ed?utm_campaign=x", title: "Op-ed", text: ARTICLE_TEXT }
  end

  test "starts a map run when the source has no map yet" do
    assert_enqueued_with(job: GenerateQuestionsJob) do
      post api_v1_maps_path, params: @params, headers: auth_headers(@user), as: :json
    end
    assert_response :accepted
    run = GenerationRun.find(response.parsed_body["run_id"])
    assert_equal "map", run.kind
    assert_equal ARTICLE_TEXT, Rails.cache.read(run.text_cache_key)
  end

  test "shares a source's completed map with every reader, judged answers hidden" do
    source = Source.for_page!(url: @params[:url], title: "Op-ed", text: ARTICLE_TEXT)
    run = create_map_run(source: source)

    assert_no_enqueued_jobs do
      post api_v1_maps_path, params: @params, headers: auth_headers(@user), as: :json
    end
    assert_response :ok
    map = response.parsed_body["map"]
    assert_equal run.id, map["run_id"]
    assert map["reconstruction"]
    assert_equal "A1", map["largest_gap"]
    assert_in_delta 0.9, map.dig("assumptions", 0, "necessity", "value")
    challenge = map["challenges"].first
    assert_equal false, challenge["revealed"]
    assert_not challenge.key?("judged")
    assert_equal %w[label text], challenge["options"].first.keys.sort
  end

  test "answering a challenge reveals the judged answer and the crowd; only the first answer counts" do
    run = create_map_run
    Learning::ChallengeAnswer.create!(user: User.create!, generation_run: run, challenge_index: 0, choice: "B")

    post api_v1_map_challenge_answer_path(run, 0), params: { choice: "d" }, headers: auth_headers(@user), as: :json
    assert_response :created
    body = response.parsed_body
    assert_equal [ "D", true, "B" ], [ body["chosen"], body["revealed"], body.dig("judged", "label") ]
    assert_equal({ "A" => 0, "B" => 1, "C" => 0, "D" => 1, "E" => 0 }, body["crowd"])
    assert body["options"].first.key?("support_delta")

    post api_v1_map_challenge_answer_path(run, 0), params: { choice: "B" }, headers: auth_headers(@user), as: :json
    assert_equal "D", response.parsed_body["chosen"]

    get api_v1_map_path(run), headers: auth_headers(@user)
    revealed = response.parsed_body["challenges"].map { _1["revealed"] }
    assert_equal [ true, false, false ], revealed
  end

  test "rejects bad choices, unknown challenges and unfinished maps" do
    run = create_map_run
    post api_v1_map_challenge_answer_path(run, 0), params: { choice: "Z" }, headers: auth_headers(@user), as: :json
    assert_response :unprocessable_entity

    post api_v1_map_challenge_answer_path(run, 9), params: { choice: "A" }, headers: auth_headers(@user), as: :json
    assert_response :not_found

    running = GenerationRun.create!(user: @user, kind: "map", status: "running")
    get api_v1_map_path(running), headers: auth_headers(@user)
    assert_response :not_found
  end
end
