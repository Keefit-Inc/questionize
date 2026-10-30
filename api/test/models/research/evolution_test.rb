require "test_helper"
require_relative "../../support/research_fixture"

class ResearchEvolutionTest < ActiveSupport::TestCase
  include ActiveJob::TestHelper
  include ResearchFixture

  test "policy payloads are bounded, hashed and immutable" do
    policy = Research::PolicyVersion.create!(version: 1, payload: { "except_mode" => "legacy" })
    assert_equal Research.digest({ "except_mode" => "legacy" }), policy.content_hash
    assert_not policy.update(payload: { "except_mode" => "abstain" })
    assert_not Research::PolicyVersion.new(version: 2, payload: { "code" => "run anything" }).valid?
    assert_not Research::PolicyVersion.new(version: 2, payload: { "except_mode" => "legacy" }, content_hash: "wrong").valid?
  end

  test "benchmark rejects source wording and mutable evidence" do
    _, benchmark = configure_research
    assert_not benchmark.update(cases: [])
    cases = replay_cases
    cases.first["question"] = "source words must never enter the registry"
    assert_not Research::Benchmark.new(name: "unsafe", cases: cases).valid?
    cases = replay_cases
    cases.last["baseline_answer"] = "A"
    assert_not Research::Benchmark.new(name: "changed legacy evidence", cases: cases).valid?
  end

  test "one active cycle and a daily attempt budget bound proposal work" do
    configure_research
    cycle = Research::StartCycle.call
    assert_raises(Research::StartCycle::Unavailable) { Research::StartCycle.call }
    cycle.update!(status: "held")
    second = Research::StartCycle.call
    second.update!(status: "failed")
    assert_raises(Research::StartCycle::Unavailable) { Research::StartCycle.call }
  end

  test "trusted independent sources can trigger an automatic batch; unknown keys cannot" do
    release, = configure_research
    settings = Rails.configuration.x.research_evolution
    old = settings.enabled
    settings.enabled = true
    3.times do |i|
      Knowledge::SourceObservation.create!(knowledge_origin: "user_experience", evidence_status: "confirmed", source_kind: "print_scan", source_ref: "source-#{i}", extractor: "offline",
        observed: { family: "CR", level: "gmat", key_verdict: "unchecked" }, leak_checks: { passed: true })
    end
    assert_raises(Research::StartCycle::Unavailable) { Research::StartCycle.call(automatic: true) }
    Knowledge::SourceObservation.all.each { _1.update!(observed: { family: "CR", level: "gmat", key_verdict: "book" }) }
    cycle = Research::StartCycle.call(automatic: true)
    assert_equal "usage_batch", cycle.trigger
    assert_equal 3, cycle.source_snapshot["trusted_sources"]
    assert_equal 35, cycle.criteria["min_cases"]
    assert_not_nil release.reload.last_automatic_at
  ensure
    settings.enabled = old
  end

  test "evidence events enqueue a debounced readiness check instead of making model calls" do
    settings = Rails.configuration.x.research_evolution
    old = settings.enabled
    settings.enabled = true
    assert_enqueued_jobs 1, only: Research::ScheduleJob do
      3.times { Research::Evidence.request_check }
    end
  ensure
    settings.enabled = old
  end

  test "a committed GMAT CR capture schedules readiness without sending source text to a model" do
    settings = Rails.configuration.x.research_evolution
    old = settings.enabled
    settings.enabled = true
    assert_enqueued_jobs 1, only: Research::ScheduleJob do
      Knowledge::SourceObservation.create!(knowledge_origin: "user_experience", evidence_status: "confirmed", source_kind: "print_scan", source_ref: "keyed-source", extractor: "offline",
        observed: { family: "CR", level: "gmat", key_verdict: "book" }, leak_checks: { passed: true })
    end
  ensure
    settings.enabled = old
  end

  test "research queue failures cannot fail the learner interaction that supplied evidence" do
    settings = Rails.configuration.x.research_evolution
    old = settings.enabled
    settings.enabled = true
    cache = Rails.cache
    Rails.cache = Class.new { def write(*) = raise(IOError, "offline queue") }.new
    assert_nil Research::Evidence.request_check
  ensure
    Rails.cache = cache if cache
    settings.enabled = old
  end
end
