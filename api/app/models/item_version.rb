class ItemVersion < ApplicationRecord
  LABELS = %w[A B C D E].freeze
  AUTHOR_KINDS = %w[agent user].freeze

  belongs_to :item
  belongs_to :parent_version, class_name: "ItemVersion", optional: true
  belongs_to :blueprint_version, class_name: "Knowledge::BlueprintVersion", optional: true
  has_many :choice_tallies, class_name: "Learning::ChoiceTally", dependent: :destroy
  has_many :judge_measurements, dependent: :destroy
  has_many :feedbacks, dependent: :destroy

  validates :version, presence: true, uniqueness: { scope: :item_id }
  validates :passage, :stem, :explanation, presence: true
  validates :correct_label, inclusion: { in: LABELS }
  validates :author_kind, inclusion: { in: AUTHOR_KINDS }
  validate :one_choice_and_rationale_per_label

  # A version from an AI "question" payload ({question, verification, judge}), with its
  # Argument Judge measurements.
  def self.create_from_generated!(item:, generated:, version:, parent: nil)
    q = generated.fetch("question")
    judge = generated["judge"]
    record = create!(
      item: item, version: version, parent_version: parent, author_kind: "agent",
      passage: q.fetch("passage"), stem: q.fetch("stem"), choices: q.fetch("choices"),
      correct_label: q.fetch("correct_label"), explanation: q.fetch("explanation"),
      rationales: q.fetch("choice_rationales").map { |r| r.slice("label", "rationale", "trap") },
      skill: q["skill"], source_anchor: q["source_anchor"],
      verification: generated.fetch("verification").merge(
        "judge" => judge&.slice("judge_version", "verdict", "measure", "direction", "margin", "key_first_rate", "runner_up", "judges", "samples")
      ).compact
    )
    record.store_judge_measurements(judge)
    record
  end

  def store_judge_measurements(judge)
    return unless judge

    rows = Array(judge["options"]).flat_map do |option|
      %w[support_delta necessity].filter_map do |measure|
        m = option[measure] or next
        { item_version_id: id, label: option["label"], measure: measure, value: m["value"],
          ci_low: m["ci_low"], ci_high: m["ci_high"], judge_version: judge["judge_version"] }
      end
    end
    JudgeMeasurement.insert_all!(rows) if rows.any?
  end

  # The item as the AI service's Question schema, for re-review.
  def to_question
    {
      type: item.family, subtype: item.subtype, passage: passage, stem: stem, choices: choices,
      correct_label: correct_label, explanation: explanation,
      choice_rationales: rationales.map { |r| r.slice("label", "rationale", "trap") },
      skill: skill.to_s, source_anchor: source_anchor.to_s
    }
  end

  def tally
    counts = choice_tallies.pluck(:label, :count).to_h
    LABELS.index_with { |label| counts.fetch(label, 0) }
  end

  private

  def one_choice_and_rationale_per_label
    %w[choices rationales].each do |field|
      labels = Array(public_send(field)).map { |entry| entry["label"] }
      errors.add(field, "must have exactly one entry for each of A-E") unless labels.sort == LABELS
    end
  end
end
