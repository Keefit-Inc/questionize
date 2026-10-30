require "test_helper"
require_relative "../support/research_fixture"

class ResearchCyclesTest < ActionDispatch::IntegrationTest
  include ResearchFixture

  test "public status is aggregate-only and reading it never schedules a paid proposal" do
    configure_research
    cycle = Research::StartCycle.call
    cycle.events.create!(stage: "private", message: "Safe aggregate event", data: { "question" => "never-public", "policy_id" => "visible" })
    assert_no_enqueued_jobs do
      get "/admin/cycles"
      assert_response :success
    end
    assert_equal "no-store", response.headers["Cache-Control"]
    assert_equal false, response.parsed_body.dig("operator", "curator")
    assert_not_includes response.body, "never-public"
    assert_not_includes response.body, "solver_answer"
    assert_not_includes response.body, "rated_attempt_ids"
  end

  test "only an authenticated curator may explicitly start a proposal" do
    configure_research
    post "/api/v1/research/cycles"
    assert_response :unauthorized
    reader = User.create!
    post "/api/v1/research/cycles", headers: auth_headers(reader)
    assert_response :forbidden
    curator = User.create!(curator: true)
    assert_enqueued_jobs 1, only: Research::CycleJob do
      post "/api/v1/research/cycles", headers: auth_headers(curator), params: { policy: "not accepted from client" }
      assert_response :accepted
    end
    assert_equal curator.id, Research::Cycle.last.requested_by_id
    get "/admin/cycles", headers: auth_headers(curator)
    assert_equal true, response.parsed_body.dig("operator", "curator")
    assert_not_includes response.body, curator.api_token
  end
end
