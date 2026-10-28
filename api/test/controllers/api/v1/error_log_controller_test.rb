require "test_helper"

class Api::V1::ErrorLogControllerTest < ActionDispatch::IntegrationTest
  include ActiveJob::TestHelper

  setup { @user = User.create! }

  def make_eligible
    post api_v1_eligibility_path, params: { country: "us", age_13_plus: true }, headers: auth_headers(@user), as: :json
  end

  test "eligibility: US and 13+ unlock the error log" do
    post api_v1_eligibility_path, params: { country: "KR", age_13_plus: true }, headers: auth_headers(@user), as: :json
    assert_equal false, response.parsed_body["error_log"]
    make_eligible
    assert_equal({ "country" => "US", "error_log" => true }, response.parsed_body)
  end

  test "capture is refused until the user is eligible" do
    post api_v1_error_log_index_path, params: { image: PHOTO }, headers: auth_headers(@user), as: :json
    assert_response :forbidden
  end

  test "a capture queues a run and keeps the photo only in the cache" do
    make_eligible
    assert_enqueued_with(job: GenerateQuestionsJob) do
      post api_v1_error_log_index_path, params: { images: [ PHOTO, PHOTO ], book: "My CR Workbook", page: "42", number: "7", chosen_label: "a" },
                                        headers: auth_headers(@user), as: :json
    end
    assert_response :accepted
    run = GenerationRun.find(response.parsed_body["run_id"])
    assert_equal [ "error_log", "A", "42" ], [ run.kind, run.params["chosen_label"], run.params["page"] ]
    assert_not_includes run.params.to_json, "base64"
    assert_equal [ PHOTO, PHOTO ], JSON.parse(Rails.cache.read(run.text_cache_key))
  end

  test "rejects anything that is not one image" do
    make_eligible
    post api_v1_error_log_index_path, params: { image: "https://example.com/x.png" }, headers: auth_headers(@user), as: :json
    assert_response :unprocessable_entity
    post api_v1_error_log_index_path, params: { image: PHOTO, chosen_label: "Z" }, headers: auth_headers(@user), as: :json
    assert_response :unprocessable_entity
    post api_v1_error_log_index_path, params: { images: [ PHOTO ] * 4 }, headers: auth_headers(@user), as: :json
    assert_response :unprocessable_entity
    post api_v1_error_log_index_path, params: { image: PHOTO }, headers: auth_headers(@user), as: :json
    assert_response :accepted, "a single image from older clients still works"
  end

  test "index lists entries with practice items and the traps that keep catching the learner" do
    2.times do |i|
      run = GenerationRun.create!(user: @user, kind: "error_log", params: { "book" => "Workbook", "page" => (10 + i).to_s, "chosen_label" => "A" })
      GenerationRuns::Recorder.new(run).record(diagnosis_event)
    end
    get api_v1_error_log_index_path, headers: auth_headers(@user)
    body = response.parsed_body
    assert_equal 2, body["entries"].size
    assert_equal 2, body.dig("entries", 0, "practice").size
    assert_equal false, body.dig("entries", 0, "practice", 0, "revealed")
    assert_equal({ "irrelevant" => 2 }, body.dig("weaknesses", "traps"))
    assert_equal({ "keyword_matching" => 2 }, body.dig("weaknesses", "misconceptions"))
  end

  test "show returns one of the user's own entries with the full analysis" do
    run = GenerationRun.create!(user: @user, kind: "error_log", params: { "page" => "42", "chosen_label" => "A" })
    GenerationRuns::Recorder.new(run).record(diagnosis_event)
    entry = @user.error_log_entries.sole

    get api_v1_error_log_path(entry), headers: auth_headers(@user)
    body = response.parsed_body
    assert_equal [ 3, "C" ], [ body.dig("diagnosis", "difficulty"), body.dig("diagnosis", "key_guess") ]
    assert_equal 5, body.dig("diagnosis", "option_reviews").size

    get api_v1_error_log_path(entry), headers: auth_headers(User.create!)
    assert_response :not_found
  end

  test "the printed question is handed to the learner's device once, then it is gone" do
    run = GenerationRun.create!(user: @user, kind: "error_log", params: {})
    GenerationRuns::Recorder.new(run).record(diagnosis_event)
    entry = @user.error_log_entries.sole

    get question_api_v1_error_log_path(entry), headers: auth_headers(User.create!)
    assert_response :not_found
    get question_api_v1_error_log_path(entry), headers: auth_headers(@user)
    assert_equal [ "Which most weakens the claim?", 5 ], [ response.parsed_body["stem"], response.parsed_body["choices"].size ]
    get question_api_v1_error_log_path(entry), headers: auth_headers(@user)
    assert_response :not_found
  end
end
