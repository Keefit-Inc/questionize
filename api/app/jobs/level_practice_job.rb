# Writes practice questions for one level from an abstract design: a snapped question's design
# re-pitched for other levels, or a hand-written seed design (db/seeds/designs.json). The design
# holds no source wording, so the questions join the shared bank once verified.
class LevelPracticeJob < ApplicationJob
  queue_as :default

  DESIGN_FIELDS = %w[family subtype competency stimulus_features key_rule distractor_traps difficulty_drivers stated_level].freeze

  # Swappable in tests, like GenerateQuestionsJob.
  class_attribute :ai_client_factory, default: -> { AiService::Client.new }

  def perform(design:, level:, practice_trap: nil, count: 1, origin: "snap")
    run = GenerationRun.create!(kind: "practice", status: "running",
                                params: { "level" => level, "origin" => origin, "subtype" => design["subtype"] })
    result = ai_client_factory.call.practice(
      "design" => design.slice(*DESIGN_FIELDS), "practice_trap" => practice_trap, "level" => level, "count" => count,
      "capability_policy" => run.params["capability_policy"]
    )
    recorder = GenerationRuns::Recorder.new(run)
    Array(result["practice"]).each { |generated| recorder.persist(generated, origin: "pattern") }
    run.update!(status: result["skipped"] ? "declined" : "completed", result: result.slice("skipped").merge("count" => run.items.count))
  rescue AiService::Error => e
    Rails.logger.error("[LevelPracticeJob] #{level}: #{e.message}")
    run&.update!(status: "failed")
  end

  # Every level in the fan-out list except the learner's own, for a design that passed the leak checks.
  def self.fan_out(observation, learner_level:)
    design = observation.observed.slice(*DESIGN_FIELDS)
    ((Rails.configuration.x.practice_fanout_levels & Level::ALL) - [ learner_level ]).each do |level|
      perform_later(design: design, level: level, practice_trap: observation.observed["chosen_trap"], origin: "snap")
    end
  end
end
