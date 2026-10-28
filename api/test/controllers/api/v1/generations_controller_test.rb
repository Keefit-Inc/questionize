require "test_helper"

class Api::V1::GenerationsControllerTest < ActionDispatch::IntegrationTest
  include ActiveJob::TestHelper

  setup do
    @user = User.create!
    @params = { url: "https://example.com/bike-lanes?utm_source=feed", title: "Bike lanes", text: ARTICLE_TEXT, types: %w[CR], difficulty: "hard" }
  end

  test "requires a bearer token" do
    post api_v1_generations_path, params: @params, as: :json
    assert_response :unauthorized
  end

  test "starts a run, caches the text and enqueues the job" do
    assert_enqueued_with(job: GenerateQuestionsJob) do
      post api_v1_generations_path, params: @params, headers: auth_headers(@user), as: :json
    end
    assert_response :accepted
    run = GenerationRun.find(response.parsed_body["run_id"])
    assert_equal @user, run.user
    assert_equal "https://example.com/bike-lanes", run.source.canonical_url
    assert_equal({ "types" => %w[CR], "difficulty" => "hard", "count_per_type" => 1 }, run.params.slice("types", "difficulty", "count_per_type"))
    assert_equal ARTICLE_TEXT, Rails.cache.read(run.text_cache_key)
    assert_not run.params.key?("text"), "article text must not be stored in the run"
  end

  test "returns verified items already in the bank without starting a run" do
    source = Source.for_page!(url: @params[:url], title: "Bike lanes", text: ARTICLE_TEXT)
    item = create_item
    item.update!(source: source)

    assert_no_enqueued_jobs do
      post api_v1_generations_path, params: @params, headers: auth_headers(@user), as: :json
    end
    assert_response :ok
    body = response.parsed_body
    assert_equal "cached", body["status"]
    assert_equal [ item.public_id ], body["items"].map { _1["id"] }
    assert_not body["items"].first.key?("correct_label")
  end

  test "rejects short text, bad urls and runs over the daily limit" do
    post api_v1_generations_path, params: @params.merge(text: "too short"), headers: auth_headers(@user), as: :json
    assert_response :unprocessable_entity

    post api_v1_generations_path, params: @params.merge(url: "chrome://newtab"), headers: auth_headers(@user), as: :json
    assert_response :unprocessable_entity

    Api::V1::GenerationsController::DAILY_LIMIT.times { GenerationRun.create!(user: @user) }
    post api_v1_generations_path, params: @params, headers: auth_headers(@user), as: :json
    assert_response :too_many_requests
  end

  test "show returns only the caller's runs" do
    run = GenerationRun.create!(user: @user, status: "completed", events: [ { "stage" => "done" } ])
    get api_v1_generation_path(run), headers: auth_headers(@user)
    assert_response :ok
    assert_equal "completed", response.parsed_body["status"]

    get api_v1_generation_path(run), headers: auth_headers(User.create!)
    assert_response :not_found
  end
end
