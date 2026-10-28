class ItemVersion < ApplicationRecord
  LABELS = %w[A B C D E].freeze
  AUTHOR_KINDS = %w[agent user].freeze

  belongs_to :item
  belongs_to :parent_version, class_name: "ItemVersion", optional: true
  belongs_to :blueprint_version, class_name: "Knowledge::BlueprintVersion", optional: true
  has_many :choice_tallies, class_name: "Learning::ChoiceTally", dependent: :destroy
  has_many :judge_measurements, dependent: :destroy

  validates :version, presence: true, uniqueness: { scope: :item_id }
  validates :passage, :stem, :explanation, presence: true
  validates :correct_label, inclusion: { in: LABELS }
  validates :author_kind, inclusion: { in: AUTHOR_KINDS }
  validate :one_choice_and_rationale_per_label

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
