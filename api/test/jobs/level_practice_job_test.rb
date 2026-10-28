require "test_helper"

class LevelPracticeJobTest < ActiveJob::TestCase
  class FakePractice
    attr_reader :payloads

    def initialize(result) = (@result = result) && (@payloads = [])

    def practice(payload)
      @payloads << payload
      @result
    end
  end

  teardown { LevelPracticeJob.ai_client_factory = -> { AiService::Client.new } }

  def design = { "family" => "CR", "subtype" => "weaken", "competency" => "Spot another cause", "key_rule" => "Names another cause", "distractor_traps" => [ "irrelevant" ], "levels" => [ "middle" ] }

  test "writes verified practice for the level into the shared bank" do
    client = FakePractice.new({ "level" => "middle", "skipped" => nil, "practice" => [ generated_question(correct: "C") ] })
    LevelPracticeJob.ai_client_factory = -> { client }
    LevelPracticeJob.perform_now(design: design, level: "middle", practice_trap: "irrelevant", count: 1, origin: "seed")

    assert_equal "middle", client.payloads.first["level"]
    assert_not client.payloads.first["design"].key?("levels"), "only design fields go to the AI service"
    item = Item.last
    assert_equal [ "middle", "public", "pattern" ], [ item.level, item.visibility, item.origin ]
    assert_equal "completed", GenerationRun.last.status
  end

  test "an out-of-scope design is recorded as declined" do
    LevelPracticeJob.ai_client_factory = -> { FakePractice.new({ "level" => "elementary", "skipped" => "subtype_out_of_scope", "practice" => [] }) }
    LevelPracticeJob.perform_now(design: design, level: "elementary")
    assert_equal "declined", GenerationRun.last.status
    assert_equal 0, Item.count
  end

  test "a snapped question's design fans out to the other levels" do
    user = User.create!(level: "high")
    run = GenerationRun.create!(user: user, kind: "error_log", params: {})
    assert_enqueued_jobs 2, only: LevelPracticeJob do
      GenerationRuns::Recorder.new(run).record(diagnosis_event)
    end
    assert_no_enqueued_jobs only: LevelPracticeJob do
      GenerationRuns::Recorder.new(GenerationRun.create!(user: user, kind: "error_log", params: {})).record(diagnosis_event(observation: false))
    end
  end

  test "the seed task queues every design for each of its levels" do
    Rails.application.load_tasks if Rake::Task.tasks.none? { _1.name == "questionize:seed_designs" }
    designs = JSON.parse(Rails.root.join("db/seeds/designs.json").read)["designs"]
    expected = designs.sum { _1["levels"].count { |l| l == "elementary" } }
    ENV["LEVELS"] = "elementary"
    assert_enqueued_jobs expected, only: LevelPracticeJob do
      assert_output(/Queued #{expected} jobs/) { Rake::Task["questionize:seed_designs"].execute }
    end
  ensure
    ENV.delete("LEVELS")
  end
end
