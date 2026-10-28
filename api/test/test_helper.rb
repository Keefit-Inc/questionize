ENV["RAILS_ENV"] ||= "test"
require_relative "../config/environment"
require "rails/test_help"

module ActiveSupport
  class TestCase
    # Run tests in parallel with specified workers
    parallelize(workers: :number_of_processors)

    # Setup all fixtures in test/fixtures/*.yml for all tests in alphabetical order.
    fixtures :all

    setup { Rails.cache.clear }

    ARTICLE_TEXT = ("City officials said new bike lanes cut accidents by 30 percent, so the mayor wants them citywide. " * 4).freeze

    def auth_headers(user)
      { "Authorization" => "Bearer #{user.api_token}" }
    end

    # The shape of a "question" event from the AI service's /v1/generate stream.
    def generated_question(correct: "B", verified: true, type: "CR", subtype: "weaken")
      {
        "id" => SecureRandom.hex(6),
        "question" => {
          "type" => type, "subtype" => subtype,
          "passage" => "Accidents fell after bike lanes were added, so bike lanes will make every street safer.",
          "stem" => "Which of the following, if true, most seriously weakens the argument?",
          "choices" => ItemVersion::LABELS.map { |l| { "label" => l, "text" => "Option #{l}" } },
          "correct_label" => correct, "explanation" => "#{correct} names an alternative cause.",
          "choice_rationales" => ItemVersion::LABELS.map { |l| { "label" => l, "rationale" => "Why #{l}", "trap" => l == correct ? "correct" : "irrelevant" } },
          "skill" => "Alternative causes", "source_anchor" => "cut accidents by 30 percent"
        },
        "verification" => { "verified" => verified, "attempts" => 1, "solver_model" => "fake", "solver_answer" => correct,
                             "solver_confidence" => 0.9, "critic_verdict" => "pass", "distractor_quality" => 4, "issues" => [], "copied_words" => 3 },
        "judge" => {
          "judge_version" => "aj-0.1:fake", "measure" => "support_delta", "direction" => "min", "verdict" => "pass",
          "margin" => 0.62, "key_first_rate" => 1.0, "runner_up" => "A", "judges" => [ "fake" ], "samples" => 6,
          "options" => ItemVersion::LABELS.map do |l|
            { "label" => l, "support_delta" => { "value" => l == correct ? -0.7 : -0.05, "ci_low" => -0.8, "ci_high" => 0.0 },
              "necessity" => { "value" => 0.2, "ci_low" => 0.1, "ci_high" => 0.3 } }
          end
        }
      }
    end

    # The shape of the "map" event payload from the AI service's /v1/map stream.
    def sample_map
      measure = ->(v) { { "value" => v, "ci_low" => v - 0.1, "ci_high" => v + 0.1 } }
      challenge = lambda do |index, kind, best|
        {
          "index" => index, "kind" => kind, "question" => "Question #{index}",
          "options" => ItemVersion::LABELS.map { |l| { "label" => l, "text" => "#{kind} #{l}", "support_delta" => measure.(l == best ? -0.7 : 0.0), "necessity" => measure.(0.2) } },
          "judged" => { "label" => best, "measure" => "support_delta", "first_rate" => 1.0, "margin" => 0.6, "runner_up" => "C" }
        }
      end
      {
        "judge_version" => "aj-0.1:fake", "scheme" => "causal",
        "conclusion" => { "text" => "Lanes make streets safer", "anchor" => "make all streets safer" },
        "premises" => [ { "id" => "P1", "text" => "Accidents fell", "anchor" => "reduced traffic accidents", "support_delta" => measure.(0.6), "necessity" => measure.(0.8) } ],
        "assumptions" => [ { "id" => "A1", "text" => "Nothing else changed", "anchor" => "", "support_delta" => measure.(0.5), "necessity" => measure.(0.9) } ],
        "largest_gap" => "A1",
        "challenges" => [ challenge.(0, "weaken", "B"), challenge.(1, "assumption", "D"), challenge.(2, "strengthen", "A") ]
      }
    end

    def create_map_run(source: nil, user: User.create!)
      GenerationRun.create!(user: user, source: source, kind: "map", status: "completed", result: sample_map)
    end

    def create_item(family: "CR", subtype: "assumption", difficulty: "medium", correct_label: "B")
      item = Item.create!(family: family, subtype: subtype, rating: Item.start_rating(difficulty))
      version = item.versions.create!(
        version: 1,
        passage: "Accidents fell after bike lanes were added, so bike lanes make streets safer.",
        stem: "The argument relies on which of the following assumptions?",
        choices: ItemVersion::LABELS.map { |l| { "label" => l, "text" => "Option #{l}" } },
        correct_label: correct_label,
        explanation: "Only #{correct_label} is required by the argument.",
        rationales: ItemVersion::LABELS.map { |l| { "label" => l, "rationale" => "Why #{l}", "trap" => l == correct_label ? "correct" : "unsupported" } }
      )
      item.update!(current_version: version)
      item
    end
  end
end
