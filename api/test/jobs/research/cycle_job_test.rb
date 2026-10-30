require "test_helper"
require_relative "../../support/research_fixture"

class ResearchCycleJobTest < ActiveJob::TestCase
  include ResearchFixture

  teardown { Research::CycleJob.ai_client_factory = -> { AiService::Client.new(read_timeout: 90) } }

  test "a passing candidate is evaluated, atomically adopted and used by the real request paths" do
    release, = configure_research
    old = release.policy_version
    client = PolicyClient.new
    Research::CycleJob.ai_client_factory = -> { client }
    cycle = Research::StartCycle.call
    Research::CycleJob.perform_now(cycle.id)
    cycle.reload

    assert_equal "adopted", cycle.status
    assert_equal cycle.candidate_policy_id, release.reload.policy_version_id
    assert_equal "abstain", release.policy_version.payload["except_mode"]
    assert_equal 2, client.probes
    assert_equal true, cycle.service_verification["verified"]
    assert_equal "active_release", cycle.service_verification["selection_source"]
    assert_equal 34, cycle.evaluation.dig("baseline", "correct")
    assert_equal 35, cycle.evaluation.dig("candidate", "correct")
    assert_equal %w[queued generating candidate evaluating gate_passed release_switched service_verified adopted], cycle.events.order(:id).pluck(:stage)
    assert_not_includes cycle.public_data.to_json, "never-public"
    assert_equal "regression", cycle.ledger_entry["evaluation_scope"]
    assert_equal 0, Item.count
    assert_equal 0, Learning::ErrorLogEntry.count

    run = GenerationRun.create!(user: User.create!(level: "gmat"), params: { "level" => "gmat", "capability_policy" => old.context })
    assert_equal release.policy_version.context, run.params["capability_policy"], "caller cannot choose an older policy"
    release.update!(policy_version: old)
    assert_equal cycle.candidate_policy.context, run.reload.params["capability_policy"], "queued requests keep their pinned version"
  end

  test "the same next candidate is compared and held without changing the active release" do
    release, = configure_research
    client = PolicyClient.new
    Research::CycleJob.ai_client_factory = -> { client }
    first = Research::StartCycle.call
    Research::CycleJob.perform_now(first.id)
    accepted_id = release.reload.policy_version_id
    second = Research::StartCycle.call
    Research::CycleJob.perform_now(second.id)

    assert_equal "held", second.reload.status
    assert_equal accepted_id, release.reload.policy_version_id
    assert_equal 35, second.evaluation.dig("baseline", "correct")
    assert_equal 35, second.evaluation.dig("candidate", "correct")
    assert_includes second.decision_reasons.join, "unchanged"
    assert_equal 2, client.probes, "a held candidate never switches or probes a new service version"
    assert_equal 2, Research::Cycle.where.not(ledger_entry: {}).count
  end

  test "failure of active service verification rolls back without deleting the candidate or evidence" do
    release, = configure_research
    original = release.policy_version_id
    client = PolicyClient.new
    client.fail_after_switch = true
    Research::CycleJob.ai_client_factory = -> { client }
    cycle = Research::StartCycle.call
    Research::CycleJob.perform_now(cycle.id)

    assert_equal "failed", cycle.reload.status
    assert_equal original, release.reload.policy_version_id
    assert_not_nil cycle.candidate_policy
    assert cycle.evaluation.present?
    assert_includes cycle.events.pluck(:stage), "rolled_back"
    assert_equal false, cycle.service_verification["verified"]
  end

  test "a stale cycle cannot overwrite a newer active policy" do
    release, = configure_research
    client = PolicyClient.new
    replacement = nil
    client.on_evaluate = lambda do
      replacement = Research::PolicyVersion.create!(version: 99, payload: { "except_mode" => "abstain" })
      release.update!(policy_version: replacement)
    end
    Research::CycleJob.ai_client_factory = -> { client }
    cycle = Research::StartCycle.call
    Research::CycleJob.perform_now(cycle.id)

    assert_equal "held", cycle.reload.status
    assert_equal replacement.id, release.reload.policy_version_id
    assert_includes cycle.decision_reasons.join, "stale"
  end

  test "a duplicate job does not issue another model proposal" do
    configure_research
    client = PolicyClient.new
    Research::CycleJob.ai_client_factory = -> { client }
    cycle = Research::StartCycle.call
    Research::CycleJob.perform_now(cycle.id)
    count = client.requests.size
    Research::CycleJob.perform_now(cycle.id)
    assert_equal count, client.requests.size
  end
end
