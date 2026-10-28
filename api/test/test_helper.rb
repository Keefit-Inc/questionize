ENV["RAILS_ENV"] ||= "test"
require_relative "../config/environment"
require "rails/test_help"

module ActiveSupport
  class TestCase
    # Run tests in parallel with specified workers
    parallelize(workers: :number_of_processors)

    # Setup all fixtures in test/fixtures/*.yml for all tests in alphabetical order.
    fixtures :all

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
