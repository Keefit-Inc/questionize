require "test_helper"
require_relative "../../support/research_fixture"

class ResearchAutomaticFlowTest < ActiveJob::TestCase
  include ResearchFixture

  setup do
    @enabled = Rails.configuration.x.research_evolution.enabled
    Rails.configuration.x.research_evolution.enabled = true
    @client = PolicyClient.new
    Research::CycleJob.ai_client_factory = -> { @client }
  end

  teardown do
    Rails.configuration.x.research_evolution.enabled = @enabled
    Research::CycleJob.ai_client_factory = -> { AiService::Client.new(read_timeout: 90) }
  end

  def drain_automatic_jobs
    perform_enqueued_jobs(only: Research::ScheduleJob, at: 2.minutes.from_now)
    perform_enqueued_jobs(only: Research::CycleJob, at: 2.minutes.from_now)
  end

  test "committed source events automatically reach proposal evaluation adoption and pinned service selection" do
    release, = configure_research
    3.times do |i|
      Knowledge::SourceObservation.create!(knowledge_origin: "user_experience", evidence_status: "confirmed", source_kind: "print_scan", source_ref: "independent-keyed-#{i}", extractor: "offline-fixture",
        observed: { family: "CR", level: "gmat", key_verdict: "book", label_source: "reference_key" }, leak_checks: { passed: true })
    end
    assert_enqueued_jobs 1, only: Research::ScheduleJob
    drain_automatic_jobs

    cycle = Research::Cycle.last
    assert_equal "usage_batch", cycle.trigger
    assert_equal "adopted", cycle.status
    assert_equal 3, cycle.source_snapshot["trusted_sources"]
    assert_equal "abstain", release.reload.policy_version.payload["except_mode"]
    assert_equal true, cycle.service_verification["verified"]
    assert_equal release.policy_version.context, GenerationRun.new(kind: "practice", params: { "level" => "gmat" }).tap(&:valid?).params["capability_policy"]
    assert_equal 0, Item.count
    assert_equal 0, Learning::ErrorLogEntry.count

    # More sources do not bypass the cooldown or cause another paid proposal.
    Rails.cache.clear
    3.times do |i|
      Knowledge::SourceObservation.create!(knowledge_origin: "user_experience", evidence_status: "confirmed", source_kind: "print_scan", source_ref: "later-keyed-#{i}", extractor: "offline-fixture",
        observed: { family: "CR", level: "gmat", key_verdict: "book" }, leak_checks: { passed: true })
    end
    drain_automatic_jobs
    assert_equal 1, Research::Cycle.count
    assert_equal 1, @client.requests.count { _1.key?("observations") }
  end

  test "model consensus does not become a trusted label even if another field claims a book key" do
    configure_research
    3.times do |i|
      Knowledge::SourceObservation.create!(knowledge_origin: "user_experience", evidence_status: "confirmed", source_kind: "print_scan", source_ref: "unconfirmed-#{i}", extractor: "offline-fixture",
        observed: { family: "CR", level: "gmat", key_verdict: "book", label_source: "model_consensus" }, leak_checks: { passed: true })
    end
    drain_automatic_jobs
    assert_equal 0, Research::Cycle.count
    assert_empty @client.requests
  end

  test "actual rated-answer events can trigger the same automatic cycle without claiming user misses are gold labels" do
    configure_research
    user = User.create!(level: "gmat")
    20.times do
      item = create_item
      Learning::RecordAttempt.call(user: user, item: item, chosen_label: "B")
    end
    drain_automatic_jobs
    cycle = Research::Cycle.last
    assert_equal "usage_batch", cycle.trigger
    assert_equal 20, cycle.source_snapshot["new_rated_attempts"]
    assert_equal 0, cycle.source_snapshot["trusted_sources"]
    assert_equal "adopted", cycle.status
    assert_equal 35, cycle.evaluation.dig("candidate", "n"), "evaluation still uses the independent frozen benchmark"
  end
end
