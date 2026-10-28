module Learning
  class ErrorLogEntry < ApplicationRecord
    belongs_to :user
    belongs_to :generation_run
    belongs_to :source_observation, class_name: "Knowledge::SourceObservation", optional: true

    validates :chosen_label, inclusion: { in: ItemVersion::LABELS }, allow_nil: true
    validates :diagnosis, presence: true
    validates :book, :page, :number, length: { maximum: 200 }

    scope :active, -> { where(archived_at: nil) }
    scope :archived, -> { where.not(archived_at: nil) }

    def practice_items
      generation_run.items.includes(:current_version, :source)
    end
  end
end
