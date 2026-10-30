require "test_helper"

class UploadLearningTest < ActionDispatch::IntegrationTest
  include ActiveJob::TestHelper

  setup do
    @release = Research::MemoryRelease.bootstrap!
    @token = "scoped-local-worker-test-token"
    Research::WorkerCredential.create!(name: "Offline test", token_digest: Digest::SHA256.hexdigest(@token))
    @headers = { "Authorization" => "Bearer #{@token}" }
  end

  teardown { Research::MemoryActivateJob.ai_client_factory = -> { AiService::Client.new(read_timeout: 90) } }

  def observe(outcome: "reference_mismatch", status: "confirmed_reference", **extra)
    Research::UploadObservation.create!(memory_version: @release.memory_version, question_fingerprint: SecureRandom.hex(32),
      reference_status: status, reference_source: "source_fixture", knowledge_origin: "expert_reference", subtype: "weaken", outcome: outcome,
      abstract_evidence: { "failure_kind" => "alternative_cause", "lesson" => "Check competing causes before accepting the attribution." },
      measurements: {}, **extra)
  end

  def lease_cycle
    observe
    Research::UploadScheduleJob.perform_now
    post "/api/v1/research/worker/lease", headers: @headers, as: :json
    assert_response :success
    @lease = response.parsed_body
    @cycle = Research::MemoryCycle.find_by!(public_id: @lease["id"])
  end

  def register_candidate
    @hashes = 12.times.map { Digest::SHA256.hexdigest("validation-#{_1}") }.sort
    training = [ Digest::SHA256.hexdigest("private-training-source") ]
    @registration = { dataset_hash: "private-dataset-hash", validation_hash: Research.digest(@hashes), training_hash: Research.digest(training),
      n_items: 12, repeats: 2, validation_label_source: "source_reference", validation_fingerprints: @hashes, training_fingerprints: training }
    post "/api/v1/research/worker/#{@cycle.public_id}/candidate", params: { lease: @lease["lease"],
      payload: { expert_rules: [ "PRIVATE_EXPERT_DERIVED_RULE" ], experience_rules: [ "Check alternative causes." ] }, registration: @registration }, headers: @headers, as: :json
    assert_response :success
    @candidate = @cycle.reload.candidate
  end

  def report(improve: true)
    proofs = [ 1, 2 ].flat_map { |round| @hashes.each_with_index.map { |hash, i| { case_hash: hash, round: round, baseline_correct: improve ? i != 0 : true, candidate_correct: true } } }
    post "/api/v1/research/worker/#{@cycle.public_id}/report", params: { lease: @lease["lease"],
      baseline_hash: @cycle.baseline.content_hash, candidate_hash: @candidate.content_hash, proofs: proofs }, headers: @headers, as: :json
  end

  test "only a scoped worker credential can receive a local research lease" do
    post "/api/v1/research/worker/lease", as: :json
    assert_response :unauthorized
    post "/api/v1/research/worker/lease", headers: auth_headers(User.create!(curator: true)), as: :json
    assert_response :unauthorized
    assert_nil Research::WorkerCredential.first.last_seen_at
  end

  test "upload signal reaches local proposal registration evaluation adoption and real request pinning" do
    lease_cycle
    assert_equal "generating", @cycle.status
    register_candidate
    client = Object.new
    client.define_singleton_method(:probe_memory) do |payload|
      memory = payload.fetch("memory")
      { "policy_id" => memory["id"], "policy_hash" => memory["hash"], "policy_version" => memory["version"], "answer_correct" => true, "runtime_version" => "gmat-upload-learning-1" }
    end
    Research::MemoryActivateJob.ai_client_factory = -> { client }
    assert_enqueued_with(job: Research::MemoryActivateJob) { report }
    assert_response :success
    perform_enqueued_jobs(only: Research::MemoryActivateJob)
    assert_equal "adopted", @cycle.reload.status
    assert_equal @candidate, @release.reload.memory_version
    run = GenerationRun.create!(kind: "error_log", params: { "level" => "gmat" })
    assert_equal @candidate.public_id, run.params["learning_policy_id"]
    assert_equal @cycle.baseline.public_id, run.params["control_policy_id"]
    assert_not_includes run.params.to_json, "PRIVATE_EXPERT_DERIVED_RULE"
    get "/admin/uploads"
    assert_response :success
    assert_not_includes response.body, "PRIVATE_EXPERT_DERIVED_RULE"
    assert_not_includes response.body, @lease["lease"]
    assert_equal 0, Item.count
  end

  test "no reproduced improvement is held without changing the running service" do
    lease_cycle
    register_candidate
    report(improve: false)
    assert_response :success
    assert_equal "held", @cycle.reload.status
    assert_equal @cycle.baseline, @release.reload.memory_version
    assert_equal 0, @cycle.evaluation["stable_gains"]
    assert_equal 2, @cycle.evaluation["rounds"].size
  end

  test "a triggered source cannot also appear in the local validation set" do
    lease_cycle
    register_candidate
    fingerprints = @hashes.dup
    fingerprints[0] = Research::UploadObservation.first.question_fingerprint
    bad = @registration.merge(validation_fingerprints: fingerprints, validation_hash: Research.digest(fingerprints.sort))
    # A second candidate is not accepted; the contamination check occurs before any mutation.
    post "/api/v1/research/worker/#{@cycle.public_id}/candidate", params: { lease: @lease["lease"], payload: { expert_rules: [], experience_rules: [] }, registration: bad }, headers: @headers, as: :json
    assert_response :unprocessable_entity
  end

  test "AI estimates and missing local workers never fabricate validation gold or adoption" do
    observe(outcome: "ai_agreement", status: "ai_estimated")
    observe(outcome: "ai_agreement", status: "ai_estimated")
    observe(outcome: "ai_agreement", status: "ai_estimated")
    Research::UploadScheduleJob.perform_now
    cycle = Research::MemoryCycle.last
    assert_equal "held", cycle.status
    assert_nil cycle.candidate
    get "/admin/uploads"
    assert_equal false, response.parsed_body.dig("worker", "online")
    assert_equal 1, response.parsed_body.dig("active_memory", "version")
  end

  test "research models reject raw question fields and encrypt private rule payloads at rest" do
    record = observe
    record.abstract_evidence = { "question" => "Raw original material" }
    assert_not record.valid?
    v = Research::MemoryVersion.create!(version: 2, parent: @release.memory_version,
      payload: { "expert_rules" => [ "PRIVATE_EXPERT_DERIVED_RULE" ], "experience_rules" => [] })
    assert_not_includes v.payload_ciphertext, "PRIVATE_EXPERT_DERIVED_RULE"
    assert_not v.update(version: 3)
  end

  test "private candidate procedures require curator authentication and are never publicly cached" do
    lease_cycle
    register_candidate
    get "/api/v1/research/memory_cycles/#{@cycle.public_id}"
    assert_response :unauthorized
    get "/api/v1/research/memory_cycles/#{@cycle.public_id}", headers: auth_headers(User.create!)
    assert_response :forbidden
    get "/api/v1/research/memory_cycles/#{@cycle.public_id}", headers: auth_headers(User.create!(curator: true))
    assert_response :success
    assert_equal "no-store", response.headers["Cache-Control"]
    assert_includes response.body, "PRIVATE_EXPERT_DERIVED_RULE"
    assert_not_includes response.body, @lease["lease"]
  end

  test "service verification failure restores the previous active version" do
    lease_cycle
    register_candidate
    client = Object.new
    client.define_singleton_method(:probe_memory) { |_payload| { "answer_correct" => false } }
    Research::MemoryActivateJob.ai_client_factory = -> { client }
    report
    perform_enqueued_jobs(only: Research::MemoryActivateJob)
    assert_equal "failed", @cycle.reload.status
    assert_equal @cycle.baseline, @release.reload.memory_version
    assert_equal false, @cycle.service_verification["verified"]
  end

  test "later confirmed reference regression rolls back but does not rewrite the measured ledger" do
    lease_cycle
    register_candidate
    report
    @cycle.finish!("adopted")
    @release.update!(memory_version: @candidate)
    frozen = @cycle.reload.ledger_entry.deep_dup
    observation = observe(memory_version: @candidate)
    observation.update!(measurements: { "main_matches_reference" => false, "control_matches_reference" => true })
    Research::UploadLearning.rollback_regression(observation)
    assert_equal @cycle.baseline, @release.reload.memory_version
    assert_equal "rolled_back", @cycle.reload.status
    assert_equal frozen, @cycle.ledger_entry
  end
end
