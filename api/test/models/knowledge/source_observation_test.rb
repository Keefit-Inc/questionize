require "test_helper"

class KnowledgeSourceObservationTest < ActiveSupport::TestCase
  include ActiveJob::TestHelper
  def observation(**attributes)
    Knowledge::SourceObservation.new(source_kind: "print_scan", source_ref: SecureRandom.hex, extractor: "test",
      observed: { "family" => "CR" }, **attributes)
  end

  test "expert references require private rights and provenance" do
    record = observation(knowledge_origin: "expert_reference", rights_scope: "shared_abstract")
    assert_not record.valid?
    assert record.errors[:provenance].any?
    assert record.errors[:rights_scope].any?
    record.assign_attributes(rights_scope: "private_research", provenance: { source_digest: "abc", derivation: "model_extracted" })
    assert record.valid?
  end

  test "memory retrieval explicitly separates origin and excludes AI estimated labels" do
    expert = observation(knowledge_origin: "expert_reference", evidence_status: "confirmed",
      provenance: { source_digest: "abc", derivation: "reference_original" }).tap(&:save!)
    usage = observation(knowledge_origin: "user_experience", evidence_status: "ai_estimated").tap(&:save!)
    assert_equal [ expert ], Knowledge::SourceObservation.memory_candidates(origin: "expert_reference").to_a
    assert_empty Knowledge::SourceObservation.memory_candidates(origin: "user_experience")
    assert_not_equal expert.knowledge_origin, usage.knowledge_origin
    assert_raises(ArgumentError) { Knowledge::SourceObservation.memory_candidates(origin: "anything") }
  end

  test "expert evidence cannot fan out to the public question bank" do
    expert = observation(knowledge_origin: "expert_reference", provenance: { source_digest: "abc", derivation: "reference_original" }).tap(&:save!)
    assert_no_enqueued_jobs(only: LevelPracticeJob) { LevelPracticeJob.fan_out(expert, learner_level: "gmat") }
  end
end
