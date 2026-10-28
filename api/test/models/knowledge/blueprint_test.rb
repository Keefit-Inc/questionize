require "test_helper"

class Knowledge::BlueprintTest < ActiveSupport::TestCase
  SPEC = {
    "objective" => { "claim" => "Distinguishes a required assumption from a supporting one" },
    "stimulus_spec" => { "length_words" => [ 60, 120 ] },
    "key_rule" => "Negating the key breaks the argument",
    "distractor_slots" => [ { "trap_pattern" => "trap.cr.strengthener-posing-as-assumption" } ]
  }.freeze

  test "revisions create numbered versions and move the current pointer" do
    blueprint = Knowledge::Blueprint.create!(key: "bp.cr.assumption.necessary-gap")
    first = blueprint.revise!(spec: SPEC, level_min: 11, level_max: 14, change_note: "initial")
    second = blueprint.revise!(spec: SPEC.merge("key_rule" => "Negation test"), level_min: 11, level_max: 14, change_note: "clarify")

    assert_equal [ 1, 2 ], [ first.version, second.version ]
    assert_equal second, blueprint.reload.current_version
  end

  test "a blueprint version needs the core spec fields" do
    blueprint = Knowledge::Blueprint.create!(key: "bp.incomplete")
    version = blueprint.versions.new(version: 1, level_min: 11, level_max: 14, spec: { "objective" => {} })
    assert_not version.valid?
    assert_match "key_rule", version.errors[:spec].first
  end

  test "status changes are recorded with a reason" do
    misconception = Knowledge::Misconception.create!(
      key: "reasoning.necessary-vs-sufficient", name: "Necessary vs sufficient",
      statement: "Treats a condition that would guarantee the conclusion as one the argument depends on",
      mechanism_family: "logic", mechanism_type: "necessary_sufficient"
    )
    misconception.transition_to!("corroborated", reason: "Observed in 3 independent sources", evidence: { "sources" => 3 })

    assert_equal "corroborated", misconception.reload.status
    event = misconception.status_events.last
    assert_equal [ "hypothesis", "corroborated" ], [ event.from_status, event.to_status ]
  end

  test "unknown statuses and mechanism families are rejected" do
    misconception = Knowledge::Misconception.new(key: "x", name: "x", statement: "x", mechanism_family: "vibes", mechanism_type: "x", status: "certain")
    assert_not misconception.valid?
    assert misconception.errors[:mechanism_family].any?
    assert misconception.errors[:status].any?
  end

  test "a competency cannot be its own prerequisite" do
    competency = Knowledge::Competency.create!(key: "vr.argument.identify-assumption", subject: "verbal_reasoning",
                                               strand: "argument_analysis", name: "Identify assumptions", level_min: 9, level_max: 14)
    edge = Knowledge::CompetencyEdge.new(competency: competency, prerequisite: competency)
    assert_not edge.valid?
  end
end
